"""CharacterBaselineLoader — loads character baselines from multiple sources.

TEMP.md §10.2: Loads from arc-level baseline files, ledgers, or workspace.
"""
import json
from pathlib import Path

from ..schemas.character_state import CharacterBaseline


class CharacterBaselineLoader:
    """Loads character baselines for drift detection."""

    def __init__(self, root: Path):
        self.root = root

    def load_all_for_arc(self, arc_id: str) -> dict[str, CharacterBaseline]:
        """Load all character baselines for an arc.

        Searches multiple candidate paths in priority order.

        Returns:
            Dict mapping character_id to CharacterBaseline

        Raises:
            FileNotFoundError if no baseline source found
        """
        candidates = [
            self.root / "arcs" / arc_id / "character_baselines.json",
            self.root / "ledgers" / "character_knowledge.json",
            self.root / "workspace" / "character_baselines" / f"{arc_id}.json",
        ]

        for path in candidates:
            if path.exists():
                return self._parse(path)

        # Fallback: create minimal baselines from draft content
        return self._infer_from_drafts(arc_id)

    def _parse(self, path: Path) -> dict[str, CharacterBaseline]:
        """Parse baseline file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        baselines = {}

        # Handle list format
        if isinstance(data, list):
            for item in data:
                cid = item.get("character_id", "")
                if cid:
                    baselines[cid] = CharacterBaseline(
                        character_id=cid,
                        display_name=item.get("display_name", cid),
                        stable_traits=item.get("stable_traits", []),
                        values=item.get("values", []),
                        taboos=item.get("taboos", []),
                        voice_markers=item.get("voice_markers", []),
                    )
        # Handle dict format
        elif isinstance(data, dict):
            for cid, info in data.items():
                if isinstance(info, dict):
                    baselines[cid] = CharacterBaseline(
                        character_id=cid,
                        display_name=info.get("display_name", cid),
                        stable_traits=info.get("stable_traits", []),
                        values=info.get("values", []),
                        taboos=info.get("taboos", []),
                    )

        return baselines

    def _infer_from_drafts(self, arc_id: str) -> dict[str, CharacterBaseline]:
        """Infer minimal baselines from draft file names."""
        drafts_dir = self.root / "arcs" / arc_id / "drafts"
        if not drafts_dir.exists():
            return {}

        # Create a minimal baseline from arc contract if available
        contract_path = self.root / "arcs" / arc_id / "arc_contract.md"
        if contract_path.exists():
            content = contract_path.read_text(encoding="utf-8", errors="replace")
            # Extract character names from contract
            names = self._extract_character_names(content)
            baselines = {}
            for name in names:
                baselines[name] = CharacterBaseline(
                    character_id=name.lower().replace(" ", "_"),
                    display_name=name,
                )
            if baselines:
                return baselines

        return {}

    @staticmethod
    def _extract_character_names(content: str) -> list[str]:
        """Extract character names from text."""
        import re
        # Look for common patterns
        names = []
        # Section headers with "character" in them
        for line in content.split("\n"):
            if "character" in line.lower() and line.startswith("#"):
                # Extract name from header
                name = line.split(":")[-1].strip().lstrip("#").strip()
                if name and name.lower() != "characters":
                    names.append(name)
        return names
