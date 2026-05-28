"""P0 tests: dry-run entry, synthetic gates, GateValidator isolation."""
import json
import pytest
from pathlib import Path
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.validators.gate_validator import GateValidator
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.diff import LedgerDiff


# P0.6: non-dry-run without gate raises ValueError
def test_non_dryrun_no_gate_raises():
    """run_novel_flow with dry_run=False and no arc_end_gate must raise ValueError."""
    from novel_workflow.crewai.flow import run_novel_flow
    with pytest.raises(ValueError, match="arc_end_gate is required"):
        run_novel_flow(project_root="/tmp/fake", dry_run=False, arc_end_gate=None)


# P0.7: dry_run=True does not raise and generates synthetic gates
def test_synthetic_gate_has_synthetic_true():
    """Synthetic gate records must have synthetic=True."""
    gate = GateRecord(
        gate_id="ae_test", gate_type="arc_end", target_artifact="test",
        decision="approved", author_input_evidence="[DRY RUN] auto-approved",
        author_id="dry_run_system", source_artifacts=[], synthetic=True,
    )
    assert gate.synthetic is True


def test_non_synthetic_gate_default():
    """Regular gate records default to synthetic=False."""
    gate = GateRecord(
        gate_id="ae_test", gate_type="arc_end", target_artifact="test",
        decision="approved", author_input_evidence="Looks good",
        author_id="author1", source_artifacts=[],
    )
    assert gate.synthetic is False


# P0.9: gate record synthetic field
def test_gate_record_serializes_synthetic():
    """Synthetic field must appear in serialized output."""
    gate = GateRecord(
        gate_id="dir_test", gate_type="direction", target_artifact="project",
        decision="approved", author_input_evidence="[DRY RUN] auto-generated",
        author_id="dry_run_system", source_artifacts=[], synthetic=True,
    )
    data = gate.model_dump(mode="json")
    assert data["synthetic"] is True


# P0.10: GateValidator rejects synthetic gate in non-dry-run apply
def test_synthetic_gate_rejected_in_non_dryrun():
    """GateValidator must reject synthetic gate when dry_run=False."""
    v = GateValidator()
    gate = GateRecord(
        gate_id="ae_test", gate_type="arc_end", target_artifact="test",
        decision="approved", author_input_evidence="[DRY RUN] auto-approved",
        author_id="dry_run_system", source_artifacts=[], synthetic=True,
    )
    with pytest.raises(ValueError, match="SYNTHETIC_GATE_REJECTED"):
        v.validate(gate, dry_run=False)


# P0.11: synthetic gate accepted in dry-run mode
def test_synthetic_gate_accepted_in_dryrun():
    """GateValidator must accept synthetic gate when dry_run=True."""
    v = GateValidator()
    gate = GateRecord(
        gate_id="ae_test", gate_type="arc_end", target_artifact="test",
        decision="approved", author_input_evidence="[DRY RUN] auto-approved",
        author_id="dry_run_system", source_artifacts=[], synthetic=True,
    )
    assert v.validate(gate, dry_run=True) is True


# AtomicApplyManager integration: synthetic gate rejected in non-dry-run apply
def test_atomic_apply_rejects_synthetic_gate_in_non_dryrun(project_root: Path):
    """AtomicApplyManager.apply must reject synthetic gate in non-dry-run mode."""
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="[DRY RUN] auto-approved",
        author_id="dry_run_system", source_artifacts=[], synthetic=True,
    )
    ledger_diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "timeline",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "A arrives"}}],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match="SYNTHETIC_GATE_REJECTED"):
        mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None, dry_run=False)


def test_atomic_apply_accepts_synthetic_gate_in_dryrun(project_root: Path):
    """AtomicApplyManager.apply must accept synthetic gate in dry-run mode."""
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="[DRY RUN] auto-approved",
        author_id="dry_run_system", source_artifacts=[], synthetic=True,
    )
    ledger_diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "timeline",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "A arrives"}}],
    )
    mgr = AtomicApplyManager(project_root)
    result = mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None, dry_run=True)
    assert result["result"] == "success"
