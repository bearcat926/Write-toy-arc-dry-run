"""Character state schemas — baseline, current state, drift findings and reports."""
from typing import Literal
from pydantic import field_validator
from .common import SchemaVersioned, Timestamped


class CharacterBaseline(SchemaVersioned):
    """Stable character traits. Created by human gate or extractor."""
    character_id: str
    display_name: str = ""
    stable_traits: list[str] = []
    core_desires: list[str] = []
    core_fears: list[str] = []
    values: list[str] = []
    taboos: list[str] = []
    decision_heuristics: list[str] = []
    voice_markers: list[str] = []
    relationship_patterns: dict[str, str] = {}
    source_artifacts: list[str] = []


class CharacterCurrentState(SchemaVersioned, Timestamped):
    """Dynamic character state for a specific arc/chapter. Derived."""
    character_id: str
    arc_id: str
    chapter_id: str = ""
    current_goal: str = ""
    current_emotional_state: str = ""
    active_misbeliefs: list[str] = []
    unresolved_residue: list[str] = []
    relationship_stances: dict[str, str] = {}
    knowledge_boundary: list[str] = []
    recent_decisions: list[str] = []
    source_artifacts: list[str] = []
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("CHARACTER_STATE_NOT_DERIVED: CharacterCurrentState must be derived")
        return v


class CharacterDriftFinding(SchemaVersioned):
    """Single drift detection finding."""
    finding_id: str
    character_id: str
    chapter_id: str
    drift_type: Literal[
        "ooc_behavior",
        "value_violation",
        "voice_drift",
        "emotional_discontinuity",
        "knowledge_boundary_violation",
        "relationship_discontinuity",
    ]
    severity: Literal["soft_warning", "creative_review", "hard_pause"]
    evidence: str
    expected_pattern: str = ""
    observed_pattern: str = ""
    source_artifact: str = ""
    recommended_action: str = ""
    can_be_intentional_design: bool = True


class CharacterDriftReport(SchemaVersioned, Timestamped):
    """Drift report for a chapter. Derived."""
    arc_id: str
    chapter_id: str
    findings: list[CharacterDriftFinding] = []
    recommended_action: Literal["approve", "revise", "creative_review", "hard_pause"] = "approve"
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("DRIFT_REPORT_NOT_DERIVED: CharacterDriftReport must be derived")
        return v
