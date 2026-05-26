import hashlib
import json
import shutil
from pathlib import Path
from ..schemas.gate import GateRecord
from ..schemas.diff import LedgerDiff, CanonDiff, ApplyRecord
from ..validators.gate_validator import GateValidator
from .canonicalizer import Canonicalizer


class AtomicApplyManager:
    def __init__(self, project_root: Path):
        self._root = project_root
        self._consumed: set[str] = set()
        self._gate_validator = GateValidator()
        self._canonicalizer = Canonicalizer(project_root)

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

        # 3. Lock (MVP: single process, no real lock needed)

        # 4. Validate not consumed
        if diff_hash in self._consumed:
            raise ValueError("ALREADY_CONSUMED: This ledger_diff has already been applied")

        # 5. Snapshot
        snapshot_dir = self._root / "arcs" / arc_id / "archive" / f"snapshot_{diff_hash[:8]}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for ledger_file in (self._root / "ledgers").glob("*.json"):
            shutil.copy2(ledger_file, snapshot_dir / ledger_file.name)

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

            # 10. Mark consumed
            self._consumed.add(diff_hash)

            return {"result": "success", "diff_hash": diff_hash}

        except Exception:
            # Rollback: restore from snapshot
            for f in snapshot_dir.glob("*.json"):
                shutil.copy2(f, self._root / "ledgers" / f.name)
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
