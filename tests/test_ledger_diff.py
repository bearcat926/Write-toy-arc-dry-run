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
