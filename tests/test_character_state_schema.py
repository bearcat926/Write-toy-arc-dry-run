"""Character state schema tests."""
import json
import pytest
from novel_workflow.schemas.character_state import (
    CharacterBaseline, CharacterCurrentState,
    CharacterDriftFinding, CharacterDriftReport,
)


def test_baseline_instantiation():
    base = CharacterBaseline(
        character_id="hero",
        display_name="Hero",
        stable_traits=["brave", "loyal"],
        values=["honor"],
        taboos=["betrayal"],
    )
    assert base.character_id == "hero"
    assert len(base.stable_traits) == 2


def test_current_state_must_be_derived():
    with pytest.raises(ValueError, match="CHARACTER_STATE_NOT_DERIVED"):
        CharacterCurrentState(
            character_id="hero", arc_id="arc_001", derived=False,
        )


def test_current_state_defaults():
    state = CharacterCurrentState(character_id="hero", arc_id="arc_001")
    assert state.derived is True
    assert state.active_misbeliefs == []


def test_drift_finding_instantiation():
    finding = CharacterDriftFinding(
        finding_id="f1", character_id="hero", chapter_id="ch_001",
        drift_type="ooc_behavior", severity="soft_warning",
        evidence="Hero acted cowardly",
    )
    assert finding.can_be_intentional_design is True


def test_drift_report_must_be_derived():
    with pytest.raises(ValueError, match="DRIFT_REPORT_NOT_DERIVED"):
        CharacterDriftReport(arc_id="arc_001", chapter_id="ch_001", derived=False)


def test_drift_report_with_findings():
    report = CharacterDriftReport(
        arc_id="arc_001", chapter_id="ch_001",
        findings=[
            CharacterDriftFinding(
                finding_id="f1", character_id="hero", chapter_id="ch_001",
                drift_type="voice_drift", severity="creative_review",
                evidence="Speech pattern changed",
            ),
        ],
        recommended_action="creative_review",
    )
    assert len(report.findings) == 1
    assert report.findings[0].severity == "creative_review"


def test_drift_report_serialization():
    report = CharacterDriftReport(
        arc_id="arc_001", chapter_id="ch_001",
        findings=[
            CharacterDriftFinding(
                finding_id="f1", character_id="hero", chapter_id="ch_001",
                drift_type="knowledge_boundary_violation", severity="hard_pause",
                evidence="Hero knows secret without being told",
            ),
        ],
        recommended_action="hard_pause",
    )
    data = json.loads(report.model_dump_json())
    assert data["derived"] is True
    assert data["findings"][0]["severity"] == "hard_pause"
