"""ForeshadowLifecycleManager — tracks foreshadow state transitions.

Creates lifecycle entries from foreshadowing ledger and updates states
based on chapter summaries.
"""
import json
from pathlib import Path

from ..schemas.foreshadow_lifecycle import (
    ForeshadowLifecycleEntry,
    ForeshadowLifecycleIndex,
    apply_transition,
    validate_transition,
)


class ForeshadowLifecycleManager:
    """Manages foreshadow lifecycle from ledgers and summaries."""

    def __init__(self, root: Path):
        self._root = root

    def build(self, arc_id: str) -> tuple[ForeshadowLifecycleIndex, list[dict]]:
        """Build lifecycle index from foreshadowing ledger and summaries.

        Returns:
            (index, invalid_transitions) — invalid_transitions is a list of
            transition attempts that were rejected.
        """
        entries: list[ForeshadowLifecycleEntry] = []

        # 1. Load foreshadowing ledger
        fs_path = self._root / "ledgers" / "foreshadowing.json"
        if not fs_path.exists():
            return ForeshadowLifecycleIndex(
                index_id=f"lifecycle_{arc_id}",
                arc_id=arc_id,
                items=[],
            ), []

        fs_data = json.loads(fs_path.read_text(encoding="utf-8"))

        # 2. Create entries from ledger
        for entry in fs_data.get("foreshadowing_entries", []):
            fs_id = entry.get("foreshadow_id", "")
            introduced_ch = entry.get("introduced_chapter", "")
            status = entry.get("status", "introduced")

            # Map ledger status to lifecycle state
            state_map = {
                "introduced": "seeded",
                "developed": "activated",
                "paid_off": "resolved",
                "abandoned": "abandoned",
            }
            initial_state = state_map.get(status, "seeded")

            lifecycle_entry = ForeshadowLifecycleEntry(
                foreshadow_id=fs_id,
                label=entry.get("summary", fs_id),
                current_state=initial_state,
                priority=entry.get("priority", "medium"),
                introduced_chapter=introduced_ch,
                last_touched_chapter=introduced_ch,
                state_history=[{
                    "from_state": "unintroduced",
                    "to_state": initial_state,
                    "chapter_id": introduced_ch,
                }],
            )
            entries.append(lifecycle_entry)

        # 3. Scan summaries for foreshadow state changes
        invalid_transitions: list[dict] = []
        summaries_dir = self._root / "workspace" / "summaries"
        if summaries_dir.exists():
            for summary_file in sorted(summaries_dir.glob("ch_*_summary.json")):
                try:
                    data = json.loads(summary_file.read_text(encoding="utf-8"))
                    ch_id = data.get("chapter_id", summary_file.stem)

                    for fs_update in data.get("foreshadow_updates", []):
                        if isinstance(fs_update, str):
                            for entry in entries:
                                if entry.foreshadow_id in fs_update:
                                    next_states = {
                                        "seeded": "activated",
                                        "latent": "activated",
                                        "activated": "escalated",
                                    }
                                    next_state = next_states.get(entry.current_state)
                                    if next_state:
                                        if validate_transition(entry.current_state, next_state):
                                            try:
                                                apply_transition(entry, next_state, ch_id)
                                            except ValueError:
                                                pass
                                        else:
                                            invalid_transitions.append({
                                                "foreshadow_id": entry.foreshadow_id,
                                                "from_state": entry.current_state,
                                                "to_state": next_state,
                                                "chapter_id": ch_id,
                                                "reason": "invalid_transition",
                                            })
                except (json.JSONDecodeError, KeyError):
                    continue

        index = ForeshadowLifecycleIndex(
            index_id=f"lifecycle_{arc_id}",
            arc_id=arc_id,
            items=entries,
        )

        # Register in manifest
        from .manifest_manager import ManifestManager
        from ..schemas.manifest import DerivedArtifactEntry
        manifest = ManifestManager(self._root)
        manifest.register_artifact(DerivedArtifactEntry(
            artifact_path="workspace/foreshadow_lifecycle_index.json",
            artifact_type="foreshadow_lifecycle_index",
            builder_name="ForeshadowLifecycleManager",
            source_artifacts=[],
        ))
        manifest.save()

        return index, invalid_transitions

    def write_index(self, arc_id: str) -> tuple:
        """Build and write lifecycle index to disk."""
        index, transitions = self.build(arc_id)
        output_path = self._root / "workspace" / "foreshadow_lifecycle_index.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
        return index, transitions
