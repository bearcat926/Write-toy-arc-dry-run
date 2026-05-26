import hashlib
import json
import shutil
from pathlib import Path
from ..schemas.gate import GateRecord
from ..schemas.diff import LedgerDiff, CanonDiff, ApplyRecord
from ..validators.gate_validator import GateValidator
from ..guards.lock_manager import LockManager
from .canonicalizer import Canonicalizer

CONSUMED_FILE = "consumed_hashes.json"


class AtomicApplyManager:
    def __init__(self, project_root: Path):
        self._root = project_root
        self._gate_validator = GateValidator()
        self._canonicalizer = Canonicalizer(project_root)
        self._consumed: set[str] = self._load_consumed()
        self._lock_manager = LockManager()

    def _load_consumed(self) -> set[str]:
        """Load consumed hashes from persistent storage."""
        path = self._root / "workspace" / CONSUMED_FILE
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return set(data.get("consumed_hashes", []))
            except (json.JSONDecodeError, KeyError):
                return set()
        return set()

    def _save_consumed(self):
        """Save consumed hashes to persistent storage."""
        path = self._root / "workspace" / CONSUMED_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"consumed_hashes": sorted(self._consumed)}, indent=2),
            encoding="utf-8",
        )

    def _diff_hash(self, diff: LedgerDiff) -> str:
        raw = json.dumps(diff.model_dump(mode='json'), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def apply(
        self,
        arc_id: str,
        gate_record: GateRecord,
        draft_files: list[str],
        ledger_diff: LedgerDiff,
        canon_diff: CanonDiff | None,
    ) -> dict:
        # 1. Validate gate
        self._gate_validator.validate(gate_record)

        # 2. Compute diff hash
        diff_hash = self._diff_hash(ledger_diff)

        # 3. Lock critical section
        with self._lock_manager.hold(f"apply_{arc_id}"):
            # 4. Validate not consumed (persistent)
            if diff_hash in self._consumed:
                raise ValueError("ALREADY_CONSUMED: This ledger_diff has already been applied")

            # 5. Snapshot ledgers + canon/manuscript + canon/characters
            snapshot_dir = self._root / "arcs" / arc_id / "archive" / f"snapshot_{diff_hash[:8]}"
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            # Snapshot ledgers
            ledgers_snap = snapshot_dir / "ledgers"
            ledgers_snap.mkdir(exist_ok=True)
            for f in (self._root / "ledgers").glob("*.json"):
                shutil.copy2(f, ledgers_snap / f.name)

            # Snapshot canon/manuscript
            manuscript_src = self._root / "canon" / "manuscript"
            manuscript_snap = snapshot_dir / "canon_manuscript"
            if manuscript_src.exists():
                if manuscript_snap.exists():
                    shutil.rmtree(manuscript_snap)
                shutil.copytree(manuscript_src, manuscript_snap)

            # Snapshot canon/characters
            characters_src = self._root / "canon" / "characters"
            characters_snap = snapshot_dir / "canon_characters"
            if characters_src.exists():
                if characters_snap.exists():
                    shutil.rmtree(characters_snap)
                shutil.copytree(characters_src, characters_snap)

            try:
                # 6. Canonicalize
                self._canonicalizer.canonicalize(arc_id, draft_files)

                # 7. Apply ledger_diff
                self._apply_ledger_diff(ledger_diff)

                # 8. Apply canon_diff (if exists)
                if canon_diff:
                    self._apply_canon_diff(canon_diff)

                # 9. Write apply record
                record = ApplyRecord(
                    arc_id=arc_id,
                    ledger_diff_hash=diff_hash,
                    canon_diff_hash="",
                    result="success",
                )
                record_path = self._root / "arcs" / arc_id / "reports" / "apply_record.json"
                record_path.write_text(json.dumps(record.model_dump(), indent=2, ensure_ascii=False, default=str))

                # 10. Mark consumed (persistent)
                self._consumed.add(diff_hash)
                self._save_consumed()

                return {"result": "success", "diff_hash": diff_hash}

            except Exception:
                # Rollback: restore ledgers + canon/manuscript + canon/characters
                for f in ledgers_snap.glob("*.json"):
                    shutil.copy2(f, self._root / "ledgers" / f.name)

                if manuscript_snap.exists():
                    if manuscript_src.exists():
                        shutil.rmtree(manuscript_src)
                    shutil.copytree(manuscript_snap, manuscript_src)

                if characters_snap.exists():
                    if characters_src.exists():
                        shutil.rmtree(characters_src)
                    shutil.copytree(characters_snap, characters_src)

                raise

    def _apply_ledger_diff(self, diff: LedgerDiff):
        for op in diff.operations:
            ledger = op["target_ledger"]
            ledger_path = self._root / "ledgers" / f"{ledger}.json"
            if not ledger_path.exists():
                ledger_path.write_text(json.dumps({"schema_version": "1.0", f"{ledger}_entries": []}, indent=2))
            data = json.loads(ledger_path.read_text())
            key = f"{ledger}_entries" if f"{ledger}_entries" in data else "events"
            if key not in data:
                data[key] = []
            data[key].append(op["data"])
            ledger_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _apply_canon_diff(self, diff: CanonDiff):
        for update in diff.character_updates:
            target = self._root / "canon" / "characters" / "character_mind_cards" / f"{update['character_id']}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(update, indent=2, ensure_ascii=False))
