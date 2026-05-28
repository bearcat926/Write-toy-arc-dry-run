"""Milestone 3.7: Apply rejects derived source tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.validators.error_codes import APPLY_DERIVED_SOURCE_REJECTED


def _make_gate():
    return GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good arc",
        author_id="local_author", source_artifacts=[],
    )


def _seed(project_root: Path):
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")


def test_derived_source_artifact_rejected_in_apply(project_root: Path):
    _seed(project_root)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_artifact": "workspace/summaries/ch_001_summary.json",
            "source_layer": "draft",
        }],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match=APPLY_DERIVED_SOURCE_REJECTED):
        mgr.apply("arc_001", _make_gate(), ["ch_001.md"], diff, None)


def test_is_derived_true_rejected_in_apply(project_root: Path):
    _seed(project_root)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_artifact": "arcs/arc_001/drafts/ch_001.md",
            "source_layer": "draft",
            "is_derived": True,
        }],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match=APPLY_DERIVED_SOURCE_REJECTED):
        mgr.apply("arc_001", _make_gate(), ["ch_001.md"], diff, None)


def test_valid_source_passes_apply(project_root: Path):
    _seed(project_root)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_artifact": "arcs/arc_001/drafts/ch_001.md",
            "source_layer": "draft",
        }],
    )
    mgr = AtomicApplyManager(project_root)
    result = mgr.apply("arc_001", _make_gate(), ["ch_001.md"], diff, None)
    assert result["result"] == "success"


def test_traces_path_rejected_in_apply(project_root: Path):
    _seed(project_root)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_artifact": "workspace/retrieval_traces/ch_001.jsonl",
        }],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match=APPLY_DERIVED_SOURCE_REJECTED):
        mgr.apply("arc_001", _make_gate(), ["ch_001.md"], diff, None)
