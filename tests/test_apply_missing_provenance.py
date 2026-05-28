"""P0-1: Apply layer must reject operations missing provenance fields."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.validators.error_codes import APPLY_MISSING_PROVENANCE


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


def test_apply_rejects_empty_source_artifact(project_root: Path):
    """Operations with empty source_artifact must be rejected."""
    _seed(project_root)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_artifact": "",
            "source_layer": "draft",
        }],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match=APPLY_MISSING_PROVENANCE):
        mgr.apply("arc_001", _make_gate(), ["ch_001.md"], diff, None)


def test_apply_rejects_missing_source_artifact_field(project_root: Path):
    """Operations without source_artifact key must be rejected."""
    _seed(project_root)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_layer": "draft",
        }],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match=APPLY_MISSING_PROVENANCE):
        mgr.apply("arc_001", _make_gate(), ["ch_001.md"], diff, None)
