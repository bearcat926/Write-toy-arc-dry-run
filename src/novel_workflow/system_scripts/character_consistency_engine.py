"""CharacterConsistencyEngine — detects character drift from chapter drafts.

First version: deterministic keyword-based detection.
Future: LLM-assisted drift detection.
"""
from pathlib import Path

from ..schemas.character_state import (
    CharacterBaseline,
    CharacterDriftFinding,
    CharacterDriftReport,
)


class CharacterConsistencyEngine:
    """Detects character drift from chapter drafts against baselines."""

    def __init__(self, root: Path):
        self._root = root

    def check_chapter(
        self,
        arc_id: str,
        chapter_id: str,
        character_id: str,
        baseline: CharacterBaseline,
    ) -> CharacterDriftReport:
        """Check a chapter draft against a character baseline.

        Args:
            arc_id: Arc identifier
            chapter_id: Chapter identifier
            character_id: Character to check
            baseline: Character baseline to check against

        Returns:
            CharacterDriftReport with findings
        """
        draft_path = self._root / "arcs" / arc_id / "drafts" / f"{chapter_id}.md"
        if not draft_path.exists():
            return CharacterDriftReport(
                arc_id=arc_id, chapter_id=chapter_id,
                findings=[], recommended_action="approve",
            )

        content = draft_path.read_text(encoding="utf-8", errors="replace").lower()
        findings: list[CharacterDriftFinding] = []
        finding_counter = 0

        # 1. Knowledge boundary violation: check if draft mentions forbidden knowledge
        for constraint in baseline.knowledge_boundary if hasattr(baseline, 'knowledge_boundary') else []:
            if constraint.lower() in content:
                finding_counter += 1
                findings.append(CharacterDriftFinding(
                    finding_id=f"drift_{chapter_id}_{finding_counter:03d}",
                    character_id=character_id,
                    chapter_id=chapter_id,
                    drift_type="knowledge_boundary_violation",
                    severity="hard_pause",
                    evidence=f"Draft mentions forbidden knowledge: '{constraint}'",
                    expected_pattern=f"Character should not know: {constraint}",
                    observed_pattern=f"Draft contains: '{constraint}'",
                    source_artifact=f"arcs/{arc_id}/drafts/{chapter_id}.md",
                    recommended_action="hard_pause",
                ))

        # 2. Taboo/violation check
        for taboo in baseline.taboos:
            if taboo.lower() in content:
                finding_counter += 1
                findings.append(CharacterDriftFinding(
                    finding_id=f"drift_{chapter_id}_{finding_counter:03d}",
                    character_id=character_id,
                    chapter_id=chapter_id,
                    drift_type="value_violation",
                    severity="creative_review",
                    evidence=f"Draft mentions taboo: '{taboo}'",
                    expected_pattern=f"Character avoids: {taboo}",
                    observed_pattern=f"Draft contains: '{taboo}'",
                    source_artifact=f"arcs/{arc_id}/drafts/{chapter_id}.md",
                    recommended_action="creative_review",
                ))

        # 3. Voice marker check
        if baseline.voice_markers:
            matched = sum(1 for marker in baseline.voice_markers if marker.lower() in content)
            match_rate = matched / len(baseline.voice_markers)
            if match_rate < 0.3:  # Less than 30% voice markers present
                finding_counter += 1
                findings.append(CharacterDriftFinding(
                    finding_id=f"drift_{chapter_id}_{finding_counter:03d}",
                    character_id=character_id,
                    chapter_id=chapter_id,
                    drift_type="voice_drift",
                    severity="soft_warning",
                    evidence=f"Only {matched}/{len(baseline.voice_markers)} voice markers found",
                    expected_pattern=f"Voice markers: {baseline.voice_markers}",
                    observed_pattern=f"Match rate: {match_rate:.0%}",
                    source_artifact=f"arcs/{arc_id}/drafts/{chapter_id}.md",
                    recommended_action="approve",
                ))

        # Determine recommended action
        if any(f.severity == "hard_pause" for f in findings):
            action = "hard_pause"
        elif any(f.severity == "creative_review" for f in findings):
            action = "creative_review"
        else:
            action = "approve"

        return CharacterDriftReport(
            arc_id=arc_id,
            chapter_id=chapter_id,
            findings=findings,
            recommended_action=action,
        )
