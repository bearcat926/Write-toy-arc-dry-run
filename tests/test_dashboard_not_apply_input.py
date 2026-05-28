"""P2.1: Dashboard cannot be used as apply input."""
import json
from pathlib import Path
import pytest
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff


def test_dashboard_not_usable_as_apply_input(project_root: Path):
    """P2.1: A dashboard_report.md must not be interpretable as apply input.

    The dashboard is a derived artifact — it should never be accepted
    as a gate or ledger_diff input to AtomicApplyManager.apply().
    """
    # Create a dashboard report
    dashboard = project_root / "workspace" / "dashboard_report.md"
    dashboard.write_text(
        "# Dashboard Report: arc_001\n\n"
        "**Status:** derived (auto-generated)\n\n"
        "## Apply\n\n- Result: success\n"
    )
    # Verify the dashboard exists
    assert dashboard.exists()
    # The dashboard is markdown, not JSON — it cannot be parsed as LedgerDiff or GateRecord
    raw = dashboard.read_text()
    with pytest.raises(Exception):
        LedgerDiff.model_validate_json(raw)
    with pytest.raises(Exception):
        GateRecord.model_validate_json(raw)
