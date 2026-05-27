import json
from pathlib import Path
from novel_workflow.system_scripts.arc_state_manager import ArcWorkingStateManager


def test_mark_chapters_rejected_cascades(project_root: Path):
    """Rejected chapters cascade to dependent AWS entries."""
    (project_root / "arcs/arc_001/arc_working_state.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "entries": [
                {"state_id": "aws_001", "source_chapter": "ch_001", "key": "k1", "value": "v1",
                 "status": "working_accepted", "depends_on": []},
                {"state_id": "aws_002", "source_chapter": "ch_002", "key": "k2", "value": "v2",
                 "status": "working_accepted", "depends_on": ["aws_001"]},
            ]
        })
    )
    mgr = ArcWorkingStateManager(project_root)
    mgr.mark_chapters_rejected("arc_001", ["ch_001"])
    aws = json.loads((project_root / "arcs/arc_001/arc_working_state.json").read_text())
    statuses = {e["state_id"]: e["status"] for e in aws["entries"]}
    assert statuses["aws_001"] == "rejected"
    assert statuses["aws_002"] == "invalidated_by_rejected_dependency"
