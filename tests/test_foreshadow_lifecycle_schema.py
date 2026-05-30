"""ForeshadowLifecycle schema tests."""
import json
import pytest
from novel_workflow.schemas.foreshadow_lifecycle import (
    ForeshadowLifecycleEntry, ForeshadowLifecycleIndex,
    validate_transition, apply_transition, VALID_TRANSITIONS,
)


def test_entry_instantiation():
    entry = ForeshadowLifecycleEntry(
        foreshadow_id="fs1", label="Broken sword",
        current_state="seeded", priority="medium",
        introduced_chapter="ch_001",
    )
    assert entry.derived is True
    assert entry.stale is False


def test_entry_must_be_derived():
    with pytest.raises(ValueError, match="FORESHADOW_NOT_DERIVED"):
        ForeshadowLifecycleEntry(
            foreshadow_id="fs1", label="test",
            current_state="seeded", priority="low",
            introduced_chapter="ch_001", derived=False,
        )


def test_index_instantiation():
    idx = ForeshadowLifecycleIndex(
        index_id="idx1", arc_id="arc_001",
        items=[ForeshadowLifecycleEntry(
            foreshadow_id="fs1", label="test",
            current_state="seeded", priority="low",
            introduced_chapter="ch_001",
        )],
    )
    assert idx.derived is True
    assert len(idx.items) == 1


def test_valid_transitions():
    assert validate_transition("seeded", "latent") is True
    assert validate_transition("seeded", "activated") is True
    assert validate_transition("seeded", "abandoned") is True
    assert validate_transition("activated", "escalated") is True
    assert validate_transition("activated", "resolved") is True
    assert validate_transition("escalated", "resolved") is True


def test_invalid_transitions():
    assert validate_transition("resolved", "activated") is False
    assert validate_transition("resolved", "abandoned") is False
    assert validate_transition("abandoned", "resolved") is False
    assert validate_transition("latent", "resolved") is False


def test_apply_transition():
    entry = ForeshadowLifecycleEntry(
        foreshadow_id="fs1", label="test",
        current_state="seeded", priority="low",
        introduced_chapter="ch_001",
    )
    entry = apply_transition(entry, "activated", "ch_005")
    assert entry.current_state == "activated"
    assert entry.last_touched_chapter == "ch_005"
    assert len(entry.state_history) == 1
    assert entry.state_history[0]["from_state"] == "seeded"
    assert entry.state_history[0]["to_state"] == "activated"


def test_apply_invalid_transition_raises():
    entry = ForeshadowLifecycleEntry(
        foreshadow_id="fs1", label="test",
        current_state="resolved", priority="low",
        introduced_chapter="ch_001",
    )
    with pytest.raises(ValueError, match="INVALID_LIFECYCLE_TRANSITION"):
        apply_transition(entry, "activated", "ch_010")


def test_terminal_states_have_no_transitions():
    assert VALID_TRANSITIONS["resolved"] == set()
    assert VALID_TRANSITIONS["abandoned"] == set()


def test_index_serialization():
    idx = ForeshadowLifecycleIndex(
        index_id="idx1", arc_id="arc_001",
        items=[ForeshadowLifecycleEntry(
            foreshadow_id="fs1", label="test",
            current_state="activated", priority="high",
            introduced_chapter="ch_001",
        )],
    )
    data = json.loads(idx.model_dump_json())
    assert data["derived"] is True
    assert data["items"][0]["current_state"] == "activated"
