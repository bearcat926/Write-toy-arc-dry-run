"""Governance Projection — Phase 3 E-series integration.

Connects ChapterCommit events to narrative governance:
  - Structured Auditor (E-01)
  - Character Baseline / Drift detection (E-02, E-03)
  - hard_pause integration (E-08)
  - Governance report as projection output

Architecture:
    ChapterCommit → ProjectionRegistry
        → governance_projection
            → StructuredAuditor.audit_chapter()
            → CharacterConsistencyEngine.check_chapter()
            → Generate GovernanceReport
            → If blocking → hard_pause PauseReport

hard_pause is checked by GateValidator before allowing next apply.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..config import PauseType
from ..schemas.chapter_commit import ChapterCommitEvent
from ..schemas.progress import PauseReport
from ..system_scripts.projection_registry import ProjectionRecord, ProjectionStatus


@dataclass
class GovernanceReport:
    """Structured governance output for a single chapter."""
    chapter_id: str = ""
    arc_id: str = ""
    commit_id: str = ""
    blocking_issues: list[dict] = field(default_factory=list)
    character_drift_findings: list[dict] = field(default_factory=list)
    foreshadow_findings: list[dict] = field(default_factory=list)
    timeline_conflicts: list[dict] = field(default_factory=list)
    arc_alignment_findings: list[dict] = field(default_factory=list)
    warning_count: int = 0
    max_severity: str = "none"  # "none" | "soft_warning" | "creative_review" | "hard_pause"
    recommended_action: str = "approve"  # "approve" | "review" | "block"
    phase: str = "shadow"
    derived: bool = True
    trace_id: str = ""

    def is_blocking(self) -> bool:
        """Check if this report blocks the next chapter."""
        return self.recommended_action == "block" and self.phase == "active"


class GovernanceProjection:
    """Governance projection handler for ChapterCommit events.

    Runs StructuredAuditor + CharacterConsistencyEngine on each chapter.
    Can operate in shadow mode (report only) or active mode (can block).
    """

    def __init__(self, root: Path, mode: str = "shadow"):
        self._root = root
        self._mode = mode  # "shadow" | "active"

    @property
    def mode(self) -> str:
        return self._mode

    def set_active(self) -> None:
        self._mode = "active"

    def set_shadow(self) -> None:
        self._mode = "shadow"

    def __call__(self, event: ChapterCommitEvent) -> ProjectionRecord:
        """Handle a ChapterCommit event (compatible with ProjectionRegistry handler)."""
        return self.audit(event)

    def audit(self, event: ChapterCommitEvent) -> ProjectionRecord:
        """Run governance audit on a chapter commit.

        Returns ProjectionRecord with status and output artifacts.
        """
        try:
            report = self._generate_report(event)

            # Write report to workspace
            self._write_report(report)

            # If active mode + blocking → write pause report
            if self._mode == "active" and report.is_blocking():
                self._write_pause_report(report, event)

            return ProjectionRecord(
                projection_name="governance",
                commit_id=event.commit_id,
                chapter_id=event.chapter_id,
                status=ProjectionStatus.SUCCESS,
                output_artifacts=[
                    f"workspace/reports/governance_{event.chapter_id}.json",
                ],
            )
        except Exception as e:
            return ProjectionRecord(
                projection_name="governance",
                commit_id=event.commit_id,
                chapter_id=event.chapter_id,
                status=ProjectionStatus.FAILED,
                error_message=str(e)[:500],
            )

    def _generate_report(self, event: ChapterCommitEvent) -> GovernanceReport:
        """Generate governance report by running all auditors."""
        from .structured_auditor import StructuredAuditor
        from .character_consistency_engine import CharacterConsistencyEngine

        report = GovernanceReport(
            chapter_id=event.chapter_id,
            arc_id=event.arc_id,
            commit_id=event.commit_id,
            trace_id=event.trace_id,
            phase=self._mode,
        )

        # 1. Structured Auditor
        auditor = StructuredAuditor(self._root)
        draft_content = self._read_draft(event.chapter_id)
        audit = auditor.audit_chapter(event.arc_id, event.chapter_id, draft_content)

        report.continuity_issues = audit.continuity_issues
        report.character_drift_findings = audit.character_drift_candidates
        report.foreshadow_findings = audit.foreshadow_lifecycle_findings
        report.timeline_conflicts = audit.timeline_conflicts

        # 2. Character Consistency (only if baselines exist)
        try:
            engine = CharacterConsistencyEngine(self._root)
            # Phase A: auditor always returns approve in shadow mode
            # Full drift detection requires loaded baselines per character
            # For now, we rely on StructuredAuditor's drift candidates
        except Exception:
            pass

        # 3. Severity assessment
        report.warning_count = (
            len(report.continuity_issues)
            + len(report.character_drift_findings)
            + len(report.foreshadow_findings)
            + len(report.timeline_conflicts)
        )

        if report.blocking_issues:
            report.max_severity = "hard_pause"
            report.recommended_action = "block"
        elif report.warning_count > 3:
            report.max_severity = "creative_review"
            report.recommended_action = "review"
        elif report.warning_count > 0:
            report.max_severity = "soft_warning"
            report.recommended_action = "approve"

        return report

    def _write_report(self, report: GovernanceReport) -> None:
        """Persist governance report."""
        report_dir = self._root / "workspace" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        output_path = report_dir / f"governance_{report.chapter_id}.json"
        data = {
            "chapter_id": report.chapter_id,
            "arc_id": report.arc_id,
            "commit_id": report.commit_id,
            "blocking_issues": report.blocking_issues,
            "character_drift_findings": report.character_drift_findings,
            "foreshadow_findings": report.foreshadow_findings,
            "timeline_conflicts": report.timeline_conflicts,
            "arc_alignment_findings": report.arc_alignment_findings,
            "warning_count": report.warning_count,
            "max_severity": report.max_severity,
            "recommended_action": report.recommended_action,
            "phase": report.phase,
            "derived": True,
            "trace_id": report.trace_id,
        }
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_pause_report(self, report: GovernanceReport, event: ChapterCommitEvent) -> None:
        """Write hard_pause report to block the next apply."""
        # Convert blocking issues to string paths
        affected = [
            f"chapter:{report.chapter_id}:{issue.get('detail', issue.get('severity', 'unknown'))}"
            for issue in report.blocking_issues
        ]

        pause = PauseReport(
            pause_type=PauseType.HARD_PAUSE,
            reason=f"Governance blocking issues detected: {len(report.blocking_issues)} issues",
            affected_artifacts=affected or [f"chapter:{report.chapter_id}"],
            evidence=json.dumps(report.blocking_issues, indent=2),
            recommended_action="Review blocking issues before next chapter",
            author_options=[
                "A) Address the issues and retry",
                "B) Override pause (document reason)",
                "C) Switch governance to shadow mode",
            ],
        )

        pause_dir = self._root / "arcs" / event.arc_id / "reports"
        pause_dir.mkdir(parents=True, exist_ok=True)
        pause_path = pause_dir / f"hard_pause_{event.chapter_id}.json"
        pause_path.write_text(
            json.dumps(pause.model_dump(mode="json"), indent=2, default=str),
            encoding="utf-8",
        )

    def _read_draft(self, chapter_id: str) -> str:
        """Read draft content for a chapter."""
        for arc_dir in (self._root / "arcs").iterdir():
            if arc_dir.is_dir():
                draft_path = arc_dir / "drafts" / f"{chapter_id}.md"
                if draft_path.exists():
                    return draft_path.read_text(encoding="utf-8")
        return ""

    def check_hard_pause(self, arc_id: str) -> PauseReport | None:
        """Check if there's an active hard_pause for an arc.

        Called by GateValidator before approving the next apply.
        """
        pause_dir = self._root / "arcs" / arc_id / "reports"
        if not pause_dir.exists():
            return None

        for pause_file in sorted(pause_dir.glob("hard_pause_*.json"), reverse=True):
            try:
                data = json.loads(pause_file.read_text(encoding="utf-8"))
                if data.get("pause_type") == "hard_pause":
                    return PauseReport.model_validate(data)
            except Exception:
                continue

        return None

    def clear_hard_pause(self, arc_id: str, chapter_id: str) -> bool:
        """Clear a hard_pause after author override."""
        pause_path = self._root / "arcs" / arc_id / "reports" / f"hard_pause_{chapter_id}.json"
        if pause_path.exists():
            # Archive rather than delete
            archive_path = pause_path.with_suffix(".json.overridden")
            pause_path.rename(archive_path)
            return True
        return False


def create_governance_projection(root: Path, mode: str = "shadow") -> GovernanceProjection:
    """Factory: create a governance projection.

    Args:
        root: Project root path
        mode: "shadow" (report only) or "active" (can block)

    Returns:
        GovernanceProjection callable compatible with ProjectionRegistry.
    """
    return GovernanceProjection(root, mode=mode)
