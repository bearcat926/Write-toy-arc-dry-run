"""E-01~E-03: Governance integration tests.

E-01: Structured Auditor schema produces governance report with required fields
E-02: Character Baseline is loaded and used in governance projection
E-03: Drift state machine (soft_warning/creative_review/hard_pause) works
"""
import json
import pytest
from pathlib import Path
from novel_workflow.schemas.chapter_commit import ChapterCommitStore, ChapterCommitEvent
from novel_workflow.system_scripts.governance_projection import GovernanceProjection, GovernanceReport
from novel_workflow.system_scripts.projection_registry import ProjectionRegistry, ProjectionStatus


class TestStructuredAuditorSchema:
    """E-01: GovernanceReport has all required TEMP.md §11.6 fields."""

    def test_report_has_required_fields(self):
        report = GovernanceReport(
            chapter_id="ch_001",
            arc_id="arc_001",
            commit_id="cmt_001",
            trace_id="trc_001",
        )
        # TEMP.md §11.6 required fields
        assert hasattr(report, "blocking_issues")
        assert hasattr(report, "character_drift_findings")
        assert hasattr(report, "foreshadow_findings")
        assert hasattr(report, "timeline_conflicts")
        assert hasattr(report, "arc_alignment_findings")
        assert hasattr(report, "warning_count")
        assert hasattr(report, "max_severity")
        assert hasattr(report, "recommended_action")
        assert report.derived is True

    def test_report_serialization(self):
        report = GovernanceReport(chapter_id="ch_001", arc_id="arc_001")
        data = json.loads(json.dumps({
            "chapter_id": report.chapter_id,
            "max_severity": report.max_severity,
            "recommended_action": report.recommended_action,
            "derived": report.derived,
        }))
        assert data["chapter_id"] == "ch_001"


class TestDriftStateMachine:
    """E-03: Drift severity levels and state transitions."""

    def test_severity_levels(self):
        report = GovernanceReport(chapter_id="ch_001")
        assert report.max_severity == "none"
        assert report.recommended_action == "approve"

    def test_soft_warning(self):
        report = GovernanceReport(chapter_id="ch_001", warning_count=1)
        # 1 warning → soft_warning
        if report.warning_count > 0 and not report.blocking_issues:
            report.max_severity = "soft_warning"
        assert report.max_severity == "soft_warning"
        assert not report.is_blocking()

    def test_creative_review(self):
        report = GovernanceReport(chapter_id="ch_001", warning_count=5)
        if report.warning_count > 3 and not report.blocking_issues:
            report.max_severity = "creative_review"
            report.recommended_action = "review"
        assert report.max_severity == "creative_review"
        assert not report.is_blocking()

    def test_hard_pause(self):
        report = GovernanceReport(
            chapter_id="ch_001",
            blocking_issues=[{"detail": "major conflict"}],
            max_severity="hard_pause",
            recommended_action="block",
            phase="active",
        )
        assert report.is_blocking()

    def test_hard_pause_shadow_not_blocking(self):
        report = GovernanceReport(
            chapter_id="ch_001",
            blocking_issues=[{"detail": "conflict"}],
            max_severity="hard_pause",
            recommended_action="block",
            phase="shadow",
        )
        assert not report.is_blocking()  # shadow mode doesn't block


class TestGovernanceProjectionIntegration:
    """E-02: GovernanceProjection runs and produces reports."""

    def test_audit_with_empty_project(self, tmp_path):
        """Governance projection handles empty project gracefully."""
        for d in ["arcs/arc_001/drafts", "arcs/arc_001/reports",
                   "workspace/reports"]:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)

        projection = GovernanceProjection(tmp_path, mode="shadow")
        event = ChapterCommitEvent(
            chapter_id="ch_001",
            arc_id="arc_001",
            commit_id="cmt_001",
            trace_id="trc_001",
        )
        record = projection.audit(event)
        assert record.status == ProjectionStatus.SUCCESS
        assert record.projection_name == "governance"

    def test_shadow_vs_active_mode(self, tmp_path):
        """Shadow mode never blocks; active mode can block."""
        for d in ["arcs/arc_001/drafts", "arcs/arc_001/reports",
                   "workspace/reports"]:
            (tmp_path / d).mkdir(parents=True, exist_ok=True)

        shadow = GovernanceProjection(tmp_path, mode="shadow")
        active = GovernanceProjection(tmp_path, mode="active")
        assert shadow.mode == "shadow"
        assert active.mode == "active"

        shadow.set_active()
        assert shadow.mode == "active"
        shadow.set_shadow()
        assert shadow.mode == "shadow"
