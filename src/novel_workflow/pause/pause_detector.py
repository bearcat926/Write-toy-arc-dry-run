from ..config import PauseType
from ..schemas.failure_event import FailureCategory, FailureEvent
from ..schemas.progress import PauseReport


class RetryPolicy:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def is_retryable(self, event: FailureEvent) -> bool:
        return event.retryable and event.retry_count < self.max_retries

    def should_pause(self, event: FailureEvent) -> bool:
        return not self.is_retryable(event)


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

    def route_failure(self, event: FailureEvent) -> PauseReport:
        """Route a failure event to the appropriate pause type."""
        # Hard pauses: security, path, gate evidence, apply validation, retry exhaustion
        if event.category in (
            FailureCategory.SECURITY_VIOLATION,
            FailureCategory.PATH_VIOLATION,
            FailureCategory.GATE_EVIDENCE_MISSING,
            FailureCategory.APPLY_VALIDATION_FAIL,
        ):
            return PauseReport(
                pause_type=PauseType.HARD_PAUSE,
                reason=f"Hard failure: {event.category.value} from {event.source}",
                affected_artifacts=[event.artifact_path] if event.artifact_path else [],
                evidence=event.evidence or event.message,
                recommended_action="Fix the issue before continuing",
                author_options=["A) Fix the issue and retry", "D) Archive current arc"],
            )

        # Creative review: canon conflict, AWS conflict, audit blocking, claim-evidence mismatch
        if event.category in (
            FailureCategory.CANON_DIRECT_CONFLICT,
            FailureCategory.AWS_CANON_CONFLICT,
            FailureCategory.AUDIT_BLOCKING,
            FailureCategory.CLAIM_EVIDENCE_MISMATCH,
        ):
            return PauseReport(
                pause_type=PauseType.CREATIVE_REVIEW,
                reason=f"Creative review needed: {event.category.value} from {event.source}",
                affected_artifacts=[event.artifact_path] if event.artifact_path else [],
                evidence=event.evidence or event.message,
                recommended_action="Review and decide",
                author_options=[
                    "A) Modify draft",
                    "B) Modify arc_contract",
                    "C) Mark as intentional, continue",
                ],
            )

        # Soft warning: chapter effect, missing evidence, schema-repairable errors
        return PauseReport(
            pause_type=PauseType.SOFT_WARNING,
            reason=f"Warning: {event.category.value} from {event.source}",
            affected_artifacts=[event.artifact_path] if event.artifact_path else [],
            evidence=event.evidence or event.message,
            recommended_action="Review and optionally revise",
            author_options=["A) Revise", "C) Accept and continue"],
        )
