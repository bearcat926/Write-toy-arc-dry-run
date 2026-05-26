import pytest
from pydantic import ValidationError
from novel_workflow.schemas.gate import GateRecord


def test_gate_record_valid():
    gate = GateRecord(
        gate_id="dir_001",
        gate_type="direction",
        target_artifact="project",
        decision="approved",
        author_input_evidence="Story direction aligns with goals",
        author_id="local_author",
        source_artifacts=["PLAN.md"],
    )
    assert gate.schema_version == "1.0"
    assert gate.decision == "approved"


def test_gate_record_missing_evidence_rejected():
    with pytest.raises(ValidationError, match="author_input_evidence"):
        GateRecord(
            gate_id="dir_001",
            gate_type="direction",
            target_artifact="project",
            decision="approved",
            author_input_evidence="",
            author_id="local_author",
            source_artifacts=[],
        )


def test_gate_record_rejected_no_evidence_required():
    gate = GateRecord(
        gate_id="dir_001",
        gate_type="direction",
        target_artifact="project",
        decision="rejected",
        author_input_evidence="",
        author_id="local_author",
        source_artifacts=[],
    )
    assert gate.decision == "rejected"
