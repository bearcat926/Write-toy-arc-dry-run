"""P1.1-P1.2: ArcWorkingStateManager + PathSafetyGuard integration tests."""
import json
import os
import pytest
from pathlib import Path
from novel_workflow.system_scripts.arc_state_manager import ArcWorkingStateManager
from novel_workflow.schemas.proposal import LedgerUpdateProposal
from novel_workflow.guards.path_safety import PathSafetyError
from tests.helpers import requires_symlink


def test_arc_state_manager_initialize_uses_guard(project_root: Path):
    """P1.1: ArcWorkingStateManager.initialize must go through PathSafetyGuard."""
    mgr = ArcWorkingStateManager(project_root)
    result = mgr.initialize("arc_001")
    assert result["schema_version"] == "1.0"
    assert (project_root / "arcs" / "arc_001" / "arc_working_state.json").exists()


def test_arc_state_manager_save_uses_guard(project_root: Path):
    """P1.1: ArcWorkingStateManager._save must go through PathSafetyGuard."""
    mgr = ArcWorkingStateManager(project_root)
    mgr.initialize("arc_001")
    # merge_proposal calls _save internally
    p = LedgerUpdateProposal(
        claim="Test", source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="Test evidence", confidence="high",
        target_ledger="timeline", operation="append_event",
        proposed_change={"event_id": "e1", "summary": "test"},
    )
    entries = mgr.merge_proposal("arc_001", p, "ch_001")
    assert len(entries) == 1
    aws = json.loads((project_root / "arcs" / "arc_001" / "arc_working_state.json").read_text())
    assert len(aws["entries"]) == 1


@requires_symlink
def test_arc_state_manager_symlink_escape_rejected(project_root: Path):
    """P1.2: If arc_working_state.json is a symlink escaping workspace, guard rejects."""
    # Create a symlink that escapes workspace
    target = project_root.parent / "outside_workspace.json"
    target.write_text('{"evil": true}')
    symlink_path = project_root / "arcs" / "arc_001" / "arc_working_state.json"
    symlink_path.parent.mkdir(parents=True, exist_ok=True)

    from tests.symlink_helper import SymlinkFallback
    with SymlinkFallback(str(target), str(symlink_path)):
        mgr = ArcWorkingStateManager(project_root)
        with pytest.raises(PathSafetyError, match="SYMLINK_ESCAPE_REJECTED"):
            mgr.initialize("arc_001")
