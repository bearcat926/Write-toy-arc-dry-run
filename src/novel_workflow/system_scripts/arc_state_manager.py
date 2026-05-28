import json
from pathlib import Path
from ..schemas.proposal import LedgerUpdateProposal
from ..guards.path_safety import PathSafetyGuard


class ArcWorkingStateManager:
    def __init__(self, project_root: Path):
        self._root = project_root
        self._guard = PathSafetyGuard(project_root)

    def initialize(self, arc_id: str) -> dict:
        aws_path = self._root / "arcs" / arc_id / "arc_working_state.json"
        self._guard.check_write_path(f"arcs/{arc_id}/arc_working_state.json", "system_script", artifact_type="arc_working_state")
        aws = {"schema_version": "1.0", "entries": []}
        aws_path.write_text(json.dumps(aws, indent=2, ensure_ascii=False))
        return aws

    def _load(self, arc_id: str) -> dict:
        path = self._root / "arcs" / arc_id / "arc_working_state.json"
        return json.loads(path.read_text())

    def _save(self, arc_id: str, aws: dict):
        path = self._root / "arcs" / arc_id / "arc_working_state.json"
        self._guard.check_write_path(f"arcs/{arc_id}/arc_working_state.json", "system_script", artifact_type="arc_working_state")
        path.write_text(json.dumps(aws, indent=2, ensure_ascii=False))

    def merge_proposal(self, arc_id: str, proposal: LedgerUpdateProposal, chapter: str) -> list[dict]:
        aws = self._load(arc_id)
        entry = {
            "state_id": f"aws_{len(aws['entries']) + 1:03d}",
            "source_chapter": chapter,
            "key": f"{proposal.target_ledger}:{proposal.operation}:{proposal.proposed_change.get('event_id', proposal.proposed_change.get('knowledge', 'unknown'))}",
            "value": proposal.proposed_change,
            "status": "working_accepted",
            "approval_scope": "arc_internal_only",
            "depends_on": [],
        }
        aws["entries"].append(entry)
        self._save(arc_id, aws)
        return [entry]

    def mark_rejected(self, arc_id: str, state_id: str):
        aws = self._load(arc_id)
        for entry in aws["entries"]:
            if entry["state_id"] == state_id:
                entry["status"] = "rejected"
            elif state_id in entry.get("depends_on", []):
                entry["status"] = "invalidated_by_rejected_dependency"
        self._save(arc_id, aws)

    def mark_chapters_rejected(self, arc_id: str, chapter_ids: list[str]):
        aws = self._load(arc_id)
        rejected_ids = {
            entry["state_id"]
            for entry in aws["entries"]
            if entry["source_chapter"] in chapter_ids
        }
        for entry in aws["entries"]:
            if entry["source_chapter"] in chapter_ids:
                entry["status"] = "rejected"
            elif any(dep in rejected_ids for dep in entry.get("depends_on", [])):
                entry["status"] = "invalidated_by_rejected_dependency"
        self._save(arc_id, aws)

    def check_canon_conflict(self, arc_id: str) -> list[dict]:
        """Compare AWS entries against canon state for key-value conflicts."""
        canon_path = self._root / "canon" / "canon_state.json"
        if not canon_path.exists():
            return []
        canon_state = json.loads(canon_path.read_text())
        aws = self._load(arc_id)
        conflicts = []
        for entry in aws.get("entries", []):
            key = entry.get("key", "")
            value = entry.get("value")
            if key in canon_state and key != "schema_version":
                if canon_state[key] != value:
                    conflicts.append({
                        "key": key,
                        "canon_value": canon_state[key],
                        "aws_value": value,
                        "state_id": entry.get("state_id", ""),
                    })
        return conflicts
