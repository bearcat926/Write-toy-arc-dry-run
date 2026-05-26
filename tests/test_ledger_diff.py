import pytest
from novel_workflow.system_scripts.ledger_diff_generator import LedgerDiffGenerator


def test_timeline_append():
    gen = LedgerDiffGenerator()
    proposals = [
        {"target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": "e1", "summary": "A arrives"}},
        {"target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": "e2", "summary": "B arrives"}},
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 2
    assert all(op["type"] == "append" for op in diff["operations"])


def test_foreshadow_valid_transition():
    gen = LedgerDiffGenerator()
    proposals = [
        {"target_ledger": "foreshadowing", "operation": "introduce_foreshadow",
         "proposed_change": {"foreshadow_id": "fs1", "summary": "broken sword", "status_from": None, "status_to": "introduced"}},
        {"target_ledger": "foreshadowing", "operation": "pay_off_foreshadow",
         "proposed_change": {"foreshadow_id": "fs1", "status_from": "introduced", "status_to": "paid_off"}},
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 2


def test_foreshadow_invalid_transition():
    gen = LedgerDiffGenerator()
    proposals = [
        {"target_ledger": "foreshadowing", "operation": "pay_off_foreshadow",
         "proposed_change": {"foreshadow_id": "fs1", "status_from": "paid_off", "status_to": "introduced"}},
    ]
    with pytest.raises(ValueError, match="INVALID_FORESHADOW_TRANSITION"):
        gen.generate(proposals)


def test_timeline_correction():
    gen = LedgerDiffGenerator()
    proposals = [
        {"target_ledger": "timeline", "operation": "correction",
         "proposed_change": {"event_id": "e1_cor", "corrects_event_id": "e1", "summary": "A arrives late"}},
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 1
    op = diff["operations"][0]
    assert op["type"] == "correction"
    assert op["data"]["corrects_event_id"] == "e1"


def test_character_knowledge_mark_corrected():
    gen = LedgerDiffGenerator()
    proposals = [
        {"target_ledger": "character_knowledge", "operation": "mark_corrected",
         "proposed_change": {"character_id": "char_a", "knowledge": "old info", "new_knowledge": "corrected info"}},
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 1
    op = diff["operations"][0]
    assert op["type"] == "mark_corrected"
    assert op["data"]["corrects_previous"] is True
