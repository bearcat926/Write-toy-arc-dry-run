"""ArcPlan schemas — arc planning, chapter beat plans, and health reports."""
from typing import Literal
from pydantic import field_validator
from .common import SchemaVersioned, Timestamped


class ArcPlan(SchemaVersioned, Timestamped):
    """Arc-level planning structure derived from arc_contract.md."""
    arc_id: str
    arc_title: str = ""
    arc_goal: str = ""
    protagonist_drive: str = ""
    main_conflict: str = ""
    chapter_range: list[str] = []
    hard_requirements: list[str] = []
    absolute_prohibitions: list[str] = []
    emotional_curve: list[dict] = []
    escalation_curve: list[dict] = []
    reveal_schedule: list[dict] = []
    payoff_schedule: list[dict] = []
    checkpoint_chapters: list[str] = []
    source_artifact: str = ""
    source_artifact_hash: str = ""
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ARC_PLAN_NOT_DERIVED: ArcPlan must be derived")
        return v


class ChapterBeatPlan(SchemaVersioned):
    """Per-chapter beat plan derived from ArcPlan."""
    arc_id: str
    chapter_id: str
    scene_goal: str = ""
    required_state_change: str = ""
    pressure_change: str = ""
    character_choice: str = ""
    promises_to_create: list[str] = []
    promises_to_payoff: list[str] = []
    allowed_reveals: list[str] = []
    forbidden_reveals: list[str] = []
    source_arc_plan: str = ""
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("BEAT_PLAN_NOT_DERIVED: ChapterBeatPlan must be derived")
        return v


class ArcHealthFinding(SchemaVersioned):
    """Single arc health finding."""
    finding_id: str
    finding_type: Literal[
        "minor_mismatch", "beat_drift", "unresolved_dependency",
        "stale_arc_plan", "trace_failure",
    ]
    chapter_id: str = ""
    severity: Literal["soft_warning", "creative_review", "hard_pause"] = "soft_warning"
    description: str = ""
    recommended_action: str = ""


class ArcHealthReport(SchemaVersioned, Timestamped):
    """Arc health report. Derived."""
    arc_id: str
    findings: list[ArcHealthFinding] = []
    status: Literal["pass", "soft_warning", "creative_review", "hard_pause"] = "pass"
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ARC_HEALTH_NOT_DERIVED: ArcHealthReport must be derived")
        return v
