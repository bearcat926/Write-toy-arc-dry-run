"""ArcPlan schema tests."""
import json
import pytest
from novel_workflow.schemas.arc_plan import (
    ArcPlan, ChapterBeatPlan, ArcHealthFinding, ArcHealthReport,
)


def test_arc_plan_instantiation():
    plan = ArcPlan(
        arc_id="arc_001", arc_goal="Hero's journey",
        hard_requirements=["must face villain"],
        absolute_prohibitions=["no deus ex machina"],
    )
    assert plan.derived is True
    assert len(plan.hard_requirements) == 1


def test_arc_plan_must_be_derived():
    with pytest.raises(ValueError, match="ARC_PLAN_NOT_DERIVED"):
        ArcPlan(arc_id="arc_001", derived=False)


def test_beat_plan_instantiation():
    beat = ChapterBeatPlan(
        arc_id="arc_001", chapter_id="ch_001",
        scene_goal="Hero discovers truth",
        required_state_change="Hero learns about betrayal",
        forbidden_reveals=["villain identity"],
    )
    assert beat.derived is True
    assert beat.forbidden_reveals == ["villain identity"]


def test_beat_plan_must_be_derived():
    with pytest.raises(ValueError, match="BEAT_PLAN_NOT_DERIVED"):
        ChapterBeatPlan(arc_id="arc_001", chapter_id="ch_001", derived=False)


def test_arc_health_finding():
    finding = ArcHealthFinding(
        finding_id="ah1", finding_type="beat_drift",
        chapter_id="ch_001", severity="creative_review",
        description="Beat not aligned with plan",
    )
    assert finding.severity == "creative_review"


def test_arc_health_report_must_be_derived():
    with pytest.raises(ValueError, match="ARC_HEALTH_NOT_DERIVED"):
        ArcHealthReport(arc_id="arc_001", derived=False)


def test_arc_health_report_serialization():
    report = ArcHealthReport(
        arc_id="arc_001",
        findings=[
            ArcHealthFinding(
                finding_id="ah1", finding_type="minor_mismatch",
                severity="soft_warning", description="Minor pacing issue",
            ),
        ],
        status="soft_warning",
    )
    data = json.loads(report.model_dump_json())
    assert data["derived"] is True
    assert data["status"] == "soft_warning"
    assert len(data["findings"]) == 1
