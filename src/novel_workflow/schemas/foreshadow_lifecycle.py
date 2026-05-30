"""ForeshadowLifecycle — tracks foreshadow state transitions.

State machine: seeded → latent → activated → escalated → resolved / abandoned
"""
from typing import Literal
from pydantic import field_validator
from .common import SchemaVersioned, Timestamped


VALID_TRANSITIONS: dict[str, set[str]] = {
    "seeded": {"latent", "activated", "abandoned"},
    "latent": {"activated", "abandoned"},
    "activated": {"escalated", "resolved", "abandoned"},
    "escalated": {"resolved", "abandoned"},
    "resolved": set(),   # terminal
    "abandoned": set(),  # terminal
}

ALL_STATES = set(VALID_TRANSITIONS.keys())


class ForeshadowLifecycleEntry(SchemaVersioned):
    """Single foreshadow lifecycle record."""
    foreshadow_id: str
    label: str
    current_state: Literal["seeded", "latent", "activated", "escalated", "resolved", "abandoned"]
    priority: Literal["low", "medium", "high", "critical"]
    introduced_chapter: str
    last_touched_chapter: str = ""
    expected_payoff_chapter: str = ""
    state_history: list[dict] = []
    stale: bool = False
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("FORESHADOW_NOT_DERIVED: ForeshadowLifecycleEntry must be derived")
        return v


class ForeshadowLifecycleIndex(SchemaVersioned, Timestamped):
    """Top-level foreshadow lifecycle index."""
    index_id: str
    arc_id: str
    items: list[ForeshadowLifecycleEntry] = []
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("FORESHADOW_INDEX_NOT_DERIVED: ForeshadowLifecycleIndex must be derived")
        return v


def validate_transition(from_state: str, to_state: str) -> bool:
    """Check if a lifecycle transition is valid."""
    if from_state not in VALID_TRANSITIONS:
        return False
    return to_state in VALID_TRANSITIONS[from_state]


def apply_transition(entry: ForeshadowLifecycleEntry, new_state: str, chapter_id: str) -> ForeshadowLifecycleEntry:
    """Apply a state transition, updating history. Raises ValueError on invalid transition."""
    if not validate_transition(entry.current_state, new_state):
        raise ValueError(
            f"INVALID_LIFECYCLE_TRANSITION: {entry.current_state} -> {new_state} "
            f"for foreshadow {entry.foreshadow_id}"
        )
    entry.state_history.append({
        "from_state": entry.current_state,
        "to_state": new_state,
        "chapter_id": chapter_id,
    })
    entry.current_state = new_state
    entry.last_touched_chapter = chapter_id
    return entry
