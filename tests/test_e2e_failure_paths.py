import json
from pathlib import Path
import pytest
from novel_workflow.guards.path_safety import PathSafetyGuard, PathSafetyError
from novel_workflow.validators.gate_validator import GateValidator
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.proposal import LedgerUpdateProposal
from novel_workflow.validators.proposal_validator import ProposalValidator


def test_path_traversal_rejected(project_root: Path):
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError) as exc_info:
        guard.check_write_path("../outside.txt", "agent")
    assert "PATH_TRAVERSAL" in str(exc_info.value)


def test_gate_evidence_missing_rejected():
    v = GateValidator()
    gate = GateRecord(
        gate_id="g1", gate_type="direction", target_artifact="project",
        decision="approved", author_input_evidence="   ",
        author_id="local_author", source_artifacts=[],
    )
    with pytest.raises(ValueError) as exc_info:
        v.validate(gate)
    assert "MISSING_GATE_EVIDENCE" in str(exc_info.value)


def test_proposal_invalid_operation(project_root: Path):
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    v = ProposalValidator(project_root)
    p = LedgerUpdateProposal(
        claim="test", source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="test evidence", confidence="high",
        target_ledger="timeline", operation="delete_event",
        proposed_change={},
    )
    result = v.validate(p)
    assert result.is_valid is False
    assert "INVALID_OPERATION" in result.error_code


def test_agent_cannot_write_canon(project_root: Path):
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError) as exc_info:
        guard.check_write_path("canon/canon_state.json", "agent")
    assert "AGENT_WRITE_DENIED" in str(exc_info.value)


def test_plugin_cannot_write_ledgers(project_root: Path):
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError) as exc_info:
        guard.check_write_path("ledgers/timeline.json", "plugin")
    assert "PLUGIN_WRITE_DENIED" in str(exc_info.value)
