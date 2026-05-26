from ..config import PauseType
from ..schemas.progress import PauseReport


class EmergencyPauseDetector:
    def detect_path_violation(self, error_code: str, path: str) -> PauseReport:
        return PauseReport(
            pause_type=PauseType.HARD_PAUSE,
            reason=f"Path safety violation: {error_code}",
            affected_artifacts=[path],
            evidence=f"Path: {path}",
            recommended_action="Fix path and retry",
            author_options=["A) Fix the issue and retry", "D) Archive current arc"],
        )

    def detect_pov_violation(self, character_id: str, knowledge: str) -> PauseReport:
        return PauseReport(
            pause_type=PauseType.CREATIVE_REVIEW,
            reason=f"POV knowledge violation: {character_id} may know {knowledge}",
            affected_artifacts=[],
            evidence=f"Character {character_id} should not know {knowledge}",
            recommended_action="Review character knowledge boundaries",
            author_options=["A) Modify draft", "B) Modify arc_contract", "C) Mark as intentional, continue"],
        )

    def detect_quality_issue(self, issue_type: str, chapter: str) -> PauseReport:
        return PauseReport(
            pause_type=PauseType.SOFT_WARNING,
            reason=f"Quality issue: {issue_type}",
            affected_artifacts=[chapter],
            evidence="",
            recommended_action="Review and revise",
            author_options=["A) Revise", "C) Accept and continue"],
        )
