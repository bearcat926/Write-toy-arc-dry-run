"""NarrativeCompressor — generates ChapterNarrativeSummary from chapter drafts.

First version: deterministic placeholder (no LLM).
Future: LLM-assisted compression with richer narrative extraction.
"""
import json
import re
from pathlib import Path

from ..schemas.narrative_summary import ChapterNarrativeSummary
from ..schemas.enums import SourceLayer
from ..schemas.hash_utils import canonical_sha256_file
from ..guards.path_safety import PathSafetyGuard


# Common character name patterns (Chinese + English)
_NAME_PATTERNS = [
    re.compile(r'[一-鿿]{2,4}(?=[说道喊叫问答笑哭叹怒惊])'),  # Chinese names before dialogue verbs
    re.compile(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b'),  # English capitalized names
]


class NarrativeCompressor:
    """Compresses chapter drafts into narrative summaries."""

    def __init__(self, root: Path):
        self._root = root
        self._guard = PathSafetyGuard(root)

    def compress(self, arc_id: str, chapter_id: str) -> ChapterNarrativeSummary:
        """Generate summary from chapter draft.

        Args:
            arc_id: Arc identifier (e.g. "arc_001")
            chapter_id: Chapter identifier (e.g. "ch_001")

        Returns:
            ChapterNarrativeSummary written to workspace/summaries/

        Raises:
            FileNotFoundError: If draft does not exist
            IOError: If hash computation or file write fails
        """
        # 1. Validate draft exists
        draft_rel = f"arcs/{arc_id}/drafts/{chapter_id}.md"
        draft_path = self._root / draft_rel
        if not draft_path.exists():
            raise FileNotFoundError(f"Draft not found: {draft_rel}")

        # 2. Read draft content
        content = draft_path.read_text(encoding="utf-8", errors="replace")

        # 3. Compute source artifact hash
        source_hash = canonical_sha256_file(draft_path)

        # 4. Extract narrative fields
        fields = self._extract_narrative_fields(content)

        # 5. Build summary
        summary = ChapterNarrativeSummary(
            chapter_id=chapter_id,
            arc_id=arc_id,
            source_layer=SourceLayer.DRAFT,
            source_artifact=draft_rel,
            source_artifact_hash=source_hash,
            **fields,
        )

        # 6. Write to workspace/summaries/
        summary_rel = f"workspace/summaries/{chapter_id}_summary.json"
        self._guard.check_write_path(summary_rel, "system_script", artifact_type="narrative_summary")
        summary_path = self._root / summary_rel
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

        return summary

    def _extract_narrative_fields(self, content: str) -> dict:
        """Deterministic extraction of narrative fields from draft content."""
        # Extract character names
        characters = set()
        for pattern in _NAME_PATTERNS:
            characters.update(pattern.findall(content))

        character_state_changes = [
            {"character": name, "change": "mentioned"} for name in sorted(characters)
        ]

        # Basic retrieval tags from first line and headings
        retrieval_tags = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                retrieval_tags.append(line.lstrip("#").strip())
            elif line and len(retrieval_tags) == 0:
                # First non-heading line as tag
                retrieval_tags.append(line[:100])
            if len(retrieval_tags) >= 5:
                break

        return {
            "causal_events": [],
            "character_state_changes": character_state_changes,
            "emotional_residue": [],
            "unresolved_tensions": [],
            "promises_created": [],
            "promises_paid_off": [],
            "foreshadow_updates": [],
            "retrieval_tags": retrieval_tags,
        }
