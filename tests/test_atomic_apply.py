import json
from pathlib import Path
import pytest
from novel_workflow.system_scripts.canonicalizer import Canonicalizer
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff, CanonDiff


def test_canonicalizer_copies_drafts(project_root: Path):
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Chapter 1")
    (project_root / "arcs/arc_001/drafts/ch_002.md").write_text("# Chapter 2")
    canon = Canonicalizer(project_root)
    canon.canonicalize("arc_001", ["ch_001.md", "ch_002.md"])
    assert (project_root / "canon/manuscript/ch_001.md").read_text() == "# Chapter 1"
    assert (project_root / "canon/manuscript/ch_002.md").read_text() == "# Chapter 2"
    assert (project_root / "arcs/arc_001/drafts/ch_001.md").exists()


def test_atomic_apply_happy_path(project_root: Path):
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "arcs/arc_001/reports/ledger_diff.json").write_text(
        json.dumps({"schema_version": "1.0", "arc_id": "arc_001",
                     "operations": [{"type": "append", "target_ledger": "timeline",
                                     "operation": "append_event",
                                     "data": {"event_id": "e1", "summary": "A arrives"}}]})
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
                     "data": {"event_id": "e1", "summary": "A arrives"}}],
    )
    mgr = AtomicApplyManager(project_root)
    result = mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)
    assert result["result"] == "success"
    assert (project_root / "canon/manuscript/ch_001.md").exists()
    assert (project_root / "arcs/arc_001/reports/apply_record.json").exists()


def test_atomic_apply_duplicate_rejected(project_root: Path):
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
                     "data": {"event_id": "e1", "summary": "A arrives"}}],
    )
    mgr = AtomicApplyManager(project_root)
    mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)
