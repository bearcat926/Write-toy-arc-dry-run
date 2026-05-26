import pytest
from pathlib import Path
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.proposal import LedgerUpdateProposal
from novel_workflow.validators.schema_validator import SchemaValidator
from novel_workflow.validators.gate_validator import GateValidator
from novel_workflow.validators.proposal_validator import ProposalValidator


def test_schema_validator_pass():
    v = SchemaValidator()
    assert v.validate({"schema_version": "1.0"}) is True


def test_schema_validator_missing():
    v = SchemaValidator()
    with pytest.raises(ValueError, match="MISSING_SCHEMA_VERSION"):
        v.validate({})


def test_schema_validator_unknown():
    v = SchemaValidator()
    with pytest.raises(ValueError, match="UNKNOWN_SCHEMA_VERSION"):
        v.validate({"schema_version": "99.0"})


def test_gate_validator_approved_with_evidence():
    v = GateValidator()
    gate = GateRecord(
        gate_id="g1", gate_type="direction", target_artifact="project",
        decision="approved", author_input_evidence="Looks good",
        author_id="local_author", source_artifacts=[],
    )
    assert v.validate(gate) is True


def test_gate_validator_approved_empty_evidence():
    v = GateValidator()
    with pytest.raises(ValueError, match="MISSING_GATE_EVIDENCE"):
        gate = GateRecord(
            gate_id="g1", gate_type="direction", target_artifact="project",
            decision="approved", author_input_evidence="  ",
            author_id="local_author", source_artifacts=[],
        )
        v.validate(gate)


def test_proposal_validator_pass(project_root: Path):
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    v = ProposalValidator(project_root)
    p = LedgerUpdateProposal(
        claim="A arrives", source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="A walked in", confidence="high",
        target_ledger="timeline", operation="append_event",
        proposed_change={"event_id": "e1"},
    )
    assert v.validate(p).is_valid is True


def test_proposal_validator_invalid_operation(project_root: Path):
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    v = ProposalValidator(project_root)
    p = LedgerUpdateProposal(
        claim="A arrives", source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="A walked in", confidence="high",
        target_ledger="timeline", operation="delete_event",
        proposed_change={},
    )
    result = v.validate(p)
    assert result.is_valid is False
    assert "INVALID_OPERATION" in result.error_code
