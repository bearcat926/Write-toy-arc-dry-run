"""Chaos testing: verify system behavior under adversarial conditions."""
import json
import pytest
from pathlib import Path
from novel_workflow.guards.path_safety import PathSafetyGuard, PathSafetyError
from novel_workflow.validators.proposal_validator import ProposalValidator
from novel_workflow.validators.gate_validator import GateValidator
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.proposal import LedgerUpdateProposal
from novel_workflow.schemas.diff import LedgerDiff


# Case 1: POV violation - character knows impossible information
def test_case1_pov_violation_proposal_validates_but_should_be_caught(project_root: Path):
    """Proposal with POV-violating claim passes schema validation but should be caught by auditor."""
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    v = ProposalValidator(project_root)
    p = LedgerUpdateProposal(
        claim="Character A knows Character B's secret identity",
        source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="A saw B's face when the mask fell",
        confidence="high",
        target_ledger="character_knowledge",
        operation="append_knowledge",
        proposed_change={"character_id": "char_a", "knowledge": "B's identity", "knowledge_source": "saw"},
    )
    # Schema validation passes (POV check is auditor's job, not validator's)
    result = v.validate(p)
    assert result.is_valid is True
    # NOTE: POV violation detection happens at the auditor/extractor level,
    # not at the proposal validator level. This is by design - the validator
    # checks schema/semantic validity, the auditor checks narrative correctness.


# Case 2: Fake evidence - evidence points to nonexistent content
def test_case2_fake_evidence_rejected(project_root: Path):
    """Proposal with evidence pointing to nonexistent artifact should be rejected."""
    v = ProposalValidator(project_root)
    p = LedgerUpdateProposal(
        claim="A killed B",
        source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_999.md",  # doesn't exist
        evidence="The blood on A's sword",
        confidence="high",
        target_ledger="timeline",
        operation="append_event",
        proposed_change={"event_id": "evt_kill", "summary": "A kills B"},
    )
    result = v.validate(p)
    assert result.is_valid is False
    assert "INVALID_SOURCE_ARTIFACT" in result.error_code
    assert result.error_category == "semantic_invalid"


# Case 2b: Evidence pointing to unsafe path
def test_case2b_unsafe_source_path_rejected(project_root: Path):
    """Proposal with traversal in source_artifact should be rejected."""
    v = ProposalValidator(project_root)
    p = LedgerUpdateProposal(
        claim="test",
        source_layer="draft",
        source_artifact="../canon/canon_state.json",
        evidence="test evidence",
        confidence="high",
        target_ledger="timeline",
        operation="append_event",
        proposed_change={"event_id": "e1", "summary": "test"},
    )
    result = v.validate(p)
    assert result.is_valid is False
    assert "UNSAFE_SOURCE_PATH" in result.error_code


# Case 3: Plugin write to canon denied
def test_case3_plugin_write_canon_denied(project_root: Path):
    """Plugin attempting to write canon/ should be denied."""
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError) as exc_info:
        guard.check_write_path("canon/canon_state.json", "plugin")
    assert "PLUGIN_WRITE_DENIED" in str(exc_info.value)


# Case 3b: Agent write to canon denied
def test_case3b_agent_write_canon_denied(project_root: Path):
    """Agent attempting to write canon/ should be denied."""
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError) as exc_info:
        guard.check_write_path("canon/canon_state.json", "agent")
    assert "AGENT_WRITE_DENIED" in str(exc_info.value)


# Case 3c: Agent write to arbs path denied (not in positive allowlist)
def test_case3c_agent_write_arbs_denied(project_root: Path):
    """Agent attempting to write to arcs root (not drafts/reviews/proposals) should be denied."""
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError) as exc_info:
        guard.check_write_path("arcs/arc_001/arc_working_state.json", "agent")
    assert "AGENT_WRITE_DENIED" in str(exc_info.value)


# Case 4: Duplicate apply rejected
def test_case4_duplicate_apply_rejected(project_root: Path):
    """Applying the same ledger_diff twice should be rejected."""
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good arc",
        author_id="local_author", source_artifacts=[],
    )
    ledger_diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "timeline",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "A arrives"},
                     "source_artifact": "arcs/arc_001/drafts/ch_001.md",
                     "source_layer": "draft"}],
    )
    mgr = AtomicApplyManager(project_root)
    # First apply succeeds
    result1 = mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)
    assert result1["result"] == "success"
    # Second apply rejected
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)


# Case 4b: Duplicate apply rejected even after restart (persistence)
def test_case4b_consumed_persists_across_manager_instances(project_root: Path):
    """Consumed hash should persist across AtomicApplyManager instances."""
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good arc",
        author_id="local_author", source_artifacts=[],
    )
    ledger_diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "timeline",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "A arrives"},
                     "source_artifact": "arcs/arc_001/drafts/ch_001.md",
                     "source_layer": "draft"}],
    )
    # First instance applies
    mgr1 = AtomicApplyManager(project_root)
    mgr1.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)
    # Second instance should reject (consumed hash persisted)
    mgr2 = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        mgr2.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)


# Case 5: Dashboard cannot be used as fact source
def test_dashboard_cannot_be_fact_source(project_root: Path):
    """Dashboard data cannot be used as canon/ledger apply input."""
    dashboard = project_root / "workspace" / "dashboard_report.md"
    dashboard.write_text("# Dashboard\n**Status:** derived\n**Source:** system script\n")
    content = dashboard.read_text()
    assert "derived" in content.lower()
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError):
        guard.check_write_path("workspace/dashboard_report.md", "system_script", artifact_type="canon_manuscript")
