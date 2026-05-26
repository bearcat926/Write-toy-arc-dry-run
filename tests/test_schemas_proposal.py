import pytest
from pydantic import ValidationError
from novel_workflow.schemas.proposal import LedgerUpdateProposal


def test_proposal_valid_timeline():
    p = LedgerUpdateProposal(
        claim="Character A arrived at location B",
        source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="A walked through the door of the tavern",
        confidence="high",
        target_ledger="timeline",
        operation="append_event",
        proposed_change={"event_id": "evt_001", "summary": "A arrives at tavern"},
    )
    assert p.operation == "append_event"


def test_proposal_missing_evidence():
    with pytest.raises(ValidationError):
        LedgerUpdateProposal(
            claim="test",
            source_layer="draft",
            source_artifact="arcs/arc_001/drafts/ch_001.md",
            evidence="",
            confidence="high",
            target_ledger="timeline",
            operation="append_event",
            proposed_change={},
        )
