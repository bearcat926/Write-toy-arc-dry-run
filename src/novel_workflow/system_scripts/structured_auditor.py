"""StructuredAuditor — Phase A: Shadow mode.

Outputs structured JSON alongside legacy markdown review.
Does NOT affect revision flow.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StructuredAuditReport:
    """Structured audit output (Phase A: shadow only)."""
    schema_version: str = "1.0"
    chapter_id: str = ""
    arc_id: str = ""
    continuity_issues: list[dict] = field(default_factory=list)
    character_drift_candidates: list[dict] = field(default_factory=list)
    foreshadow_lifecycle_findings: list[dict] = field(default_factory=list)
    timeline_conflicts: list[dict] = field(default_factory=list)
    recommended_action: str = "approve"
    phase: str = "shadow"
    derived: bool = True


class StructuredAuditor:
    """Structured auditor — Phase A (shadow only).

    Generates structured JSON report but does not affect revision flow.
    """

    def __init__(self, root: Path):
        self._root = root

    def audit_chapter(
        self,
        arc_id: str,
        chapter_id: str,
        draft_content: str = "",
    ) -> StructuredAuditReport:
        """Generate structured audit report for a chapter.

        Phase A: Always returns approve (shadow mode).
        Future phases will add actual detection logic.
        """
        report = StructuredAuditReport(
            chapter_id=chapter_id,
            arc_id=arc_id,
            recommended_action="approve",
            phase="shadow",
        )

        # Phase A: Write report to workspace for audit trail
        report_path = self._root / "workspace" / "reports"
        report_path.mkdir(parents=True, exist_ok=True)
        output = report_path / f"structured_audit_{chapter_id}.json"
        import json
        output.write_text(json.dumps(report.__dict__, indent=2, default=str), encoding="utf-8")

        return report
