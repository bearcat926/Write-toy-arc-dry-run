import pytest
from novel_workflow.system_scripts.ledger_diff_generator import LedgerDiffGenerator


def _proposal(**kwargs):
    """Helper to create a proposal dict with required provenance fields."""
    base = {
        "source_layer": "draft",
        "source_artifact": "arcs/arc_001/drafts/ch_001.md",
    }
    base.update(kwargs)
    return base


def test_timeline_append():
    gen = LedgerDiffGenerator()
    proposals = [
        _proposal(target_ledger="timeline", operation="append_event",
                  proposed_change={"event_id": "e1", "summary": "A arrives"}),
        _proposal(target_ledger="timeline", operation="append_event",
                  proposed_change={"event_id": "e2", "summary": "B arrives"}),
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 2
    assert all(op["type"] == "append" for op in diff["operations"])


def test_generator_preserves_provenance():
    """Generator must include source_layer/source_artifact in output operations."""
    gen = LedgerDiffGenerator()
    proposals = [
        _proposal(target_ledger="timeline", operation="append_event",
                  proposed_change={"event_id": "e1", "summary": "test"}),
    ]
    diff = gen.generate(proposals)
    op = diff["operations"][0]
    assert op["source_layer"] == "draft"
    assert op["source_artifact"] == "arcs/arc_001/drafts/ch_001.md"
    assert op["is_derived"] is False


def test_generator_rejects_missing_provenance():
    """Generator must reject proposals without source_layer/source_artifact."""
    gen = LedgerDiffGenerator()
    proposals = [
        {"target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": "e1", "summary": "test"}},
    ]
    with pytest.raises(ValueError, match="MISSING_PROVENANCE"):
        gen.generate(proposals)


def test_foreshadow_valid_transition():
    gen = LedgerDiffGenerator()
    proposals = [
        _proposal(target_ledger="foreshadowing", operation="introduce_foreshadow",
                  proposed_change={"foreshadow_id": "fs1", "summary": "broken sword", "status_from": None, "status_to": "introduced"}),
        _proposal(target_ledger="foreshadowing", operation="pay_off_foreshadow",
                  proposed_change={"foreshadow_id": "fs1", "status_from": "introduced", "status_to": "paid_off"}),
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 2


def test_foreshadow_invalid_transition():
    gen = LedgerDiffGenerator()
    proposals = [
        _proposal(target_ledger="foreshadowing", operation="pay_off_foreshadow",
                  proposed_change={"foreshadow_id": "fs1", "status_from": "paid_off", "status_to": "introduced"}),
    ]
    with pytest.raises(ValueError, match="INVALID_FORESHADOW_TRANSITION"):
        gen.generate(proposals)


def test_timeline_correction():
    gen = LedgerDiffGenerator()
    proposals = [
        _proposal(target_ledger="timeline", operation="correction",
                  proposed_change={"event_id": "e1_cor", "corrects_event_id": "e1", "summary": "A arrives late"}),
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 1
    op = diff["operations"][0]
    assert op["type"] == "correction"
    assert op["data"]["corrects_event_id"] == "e1"
    assert op["source_layer"] == "draft"


def test_character_knowledge_mark_corrected():
    gen = LedgerDiffGenerator()
    proposals = [
        _proposal(target_ledger="character_knowledge", operation="mark_corrected",
                  proposed_change={"character_id": "char_a", "knowledge": "old info", "new_knowledge": "corrected info"}),
    ]
    diff = gen.generate(proposals)
    assert len(diff["operations"]) == 1
    op = diff["operations"][0]
    assert op["type"] == "mark_corrected"
    assert op["data"]["corrects_previous"] is True
    assert op["source_artifact"] == "arcs/arc_001/drafts/ch_001.md"
