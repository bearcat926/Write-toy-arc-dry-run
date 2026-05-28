import json
from pathlib import Path
import pytest
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.schemas.gate import GateRecord


def test_invalid_foreshadow_transition_rejected(project_root: Path):
    """Ledger diff with invalid foreshadow transition should be rejected."""
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "ledgers/foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "foreshadowing_entries": []})
    )
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")

    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="test",
        author_id="local_author", source_artifacts=[],
    )
    ledger_diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "type": "foreshadow_transition",
            "target_ledger": "foreshadowing",
            "operation": "pay_off_foreshadow",
            "data": {"foreshadow_id": "fs1", "status_from": "paid_off", "status_to": "introduced"},
            "source_artifact": "arcs/arc_001/drafts/ch_001.md",
            "source_layer": "draft",
        }],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match="INVALID_FORESHADOW_TRANSITION"):
        mgr.apply("arc_001", gate, ["ch_001.md"], ledger_diff, None)
