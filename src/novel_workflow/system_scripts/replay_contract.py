"""ReplayContract — captures input snapshots for deterministic replay.

PatchB B-P0-03: Ensures same inputs produce same outputs.
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InputSnapshot:
    """Snapshot of inputs for a single replay."""
    contract_id: str
    arc_id: str
    chapter_id: str
    mode: str
    input_files: list[dict] = field(default_factory=list)
    context_mode: str = "legacy"
    budget: int = 0
    profile: str = "writer"
    fingerprint: str = ""


class ReplayContract:
    """Captures and validates input snapshots for deterministic replay."""

    def __init__(self, root: Path):
        self._root = root

    def capture_inputs(
        self,
        arc_id: str,
        chapter_id: str,
        mode: str,
        context_mode: str = "legacy",
        budget: int = 0,
        profile: str = "writer",
    ) -> InputSnapshot:
        """Capture current input state for replay validation."""
        input_files = []

        # Capture relevant input files
        for rel_path in self._relevant_inputs(arc_id, chapter_id):
            full_path = self._root / rel_path
            if full_path.exists():
                content = full_path.read_bytes()
                input_files.append({
                    "path": rel_path,
                    "hash": hashlib.sha256(content).hexdigest(),
                    "size": len(content),
                })

        contract_id = f"replay_{arc_id}_{chapter_id}_{mode}"
        snapshot = InputSnapshot(
            contract_id=contract_id,
            arc_id=arc_id,
            chapter_id=chapter_id,
            mode=mode,
            input_files=input_files,
            context_mode=context_mode,
            budget=budget,
            profile=profile,
        )

        # Compute fingerprint
        snapshot.fingerprint = self._compute_fingerprint(snapshot)
        return snapshot

    def validate_replay(self, original: InputSnapshot, actual: InputSnapshot) -> bool:
        """Validate that actual inputs match original for deterministic replay."""
        return original.fingerprint == actual.fingerprint

    def _relevant_inputs(self, arc_id: str, chapter_id: str) -> list[str]:
        """List input files relevant to a chapter context build."""
        return [
            "canon/approved_outline.md",
            f"arcs/{arc_id}/arc_contract.md",
            f"arcs/{arc_id}/drafts/{chapter_id}.md",
        ]

    @staticmethod
    def _compute_fingerprint(snapshot: InputSnapshot) -> str:
        """Compute deterministic fingerprint from snapshot."""
        parts = [
            snapshot.arc_id,
            snapshot.chapter_id,
            snapshot.mode,
            snapshot.context_mode,
            str(snapshot.budget),
            snapshot.profile,
        ]
        for f in sorted(snapshot.input_files, key=lambda x: x["path"]):
            parts.append(f"{f['path']}:{f['hash']}")

        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
