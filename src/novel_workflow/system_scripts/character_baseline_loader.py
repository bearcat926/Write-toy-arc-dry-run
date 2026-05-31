"""CharacterBaselineLoader — loads character baselines from multiple sources.

TEMP.md §10.2: Loads from arc-level baseline files, ledgers, or workspace.
"""
import json
from pathlib import Path

from ..schemas.character_state import CharacterBaseline


class CharacterBaselineLoader:
    """Loads character baselines for an arc from available sources."""

    def __init__(self, root: Path):
        self._root = root

    def load_all_for_arc(self, *, arc_id: str) -> dict:
        """Load all character baselines for an arc. Returns empty dict if none found."""
        candidates = [
            self._root / "arcs" / arc_id / "character_baselines.json",
            self._root / "ledgers" / "character_knowledge.json",
            self._root / "workspace" / "character_baselines" / f"{arc_id}.json",
        ]
        for path in candidates:
            if path.exists():
                return self._parse(path)
        return {}

    @staticmethod
    def _parse(path: Path) -> dict:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, list):
            entries = data
        else:
            entries = data.get("characters", data.get("entries", [data]))
        baselines = {}
        for entry in entries:
            try:
                baseline = CharacterBaseline.model_validate(entry)
                baselines[baseline.character_id] = baseline
            except Exception:
                continue
        return baselines
