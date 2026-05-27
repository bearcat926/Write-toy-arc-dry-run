import json
from pathlib import Path
from novel_workflow.system_scripts.arc_state_manager import ArcWorkingStateManager
from novel_workflow.schemas.proposal import LedgerUpdateProposal


def test_init_from_canon(project_root: Path):
    (project_root / "canon/canon_state.json").write_text(
        json.dumps({"schema_version": "1.0", "setting": "medieval tavern"})
    )
    mgr = ArcWorkingStateManager(project_root)
    aws = mgr.initialize("arc_001")
    assert aws["schema_version"] == "1.0"
    assert len(aws["entries"]) >= 0


def test_merge_proposal(project_root: Path):
    mgr = ArcWorkingStateManager(project_root)
    (project_root / "arcs/arc_001/arc_working_state.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []})
    )
    p = LedgerUpdateProposal(
        claim="A arrives", source_layer="draft",
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        evidence="A walked in", confidence="high",
        target_ledger="timeline", operation="append_event",
        proposed_change={"event_id": "e1", "summary": "A arrives at tavern"},
    )
    entries = mgr.merge_proposal("arc_001", p, "ch_001")
    assert len(entries) == 1
    assert entries[0]["status"] == "working_accepted"
    assert entries[0]["source_chapter"] == "ch_001"


def test_cascade_invalidation(project_root: Path):
    (project_root / "arcs/arc_001/arc_working_state.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "entries": [
                {"state_id": "aws_001", "source_chapter": "ch_001", "key": "k1", "value": "v1",
                 "status": "working_accepted", "depends_on": []},
                {"state_id": "aws_002", "source_chapter": "ch_002", "key": "k2", "value": "v2",
                 "status": "working_accepted", "depends_on": ["aws_001"]},
                {"state_id": "aws_003", "source_chapter": "ch_003", "key": "k3", "value": "v3",
                 "status": "working_accepted", "depends_on": []},
            ]
        })
    )
    mgr = ArcWorkingStateManager(project_root)
    mgr.mark_rejected("arc_001", "aws_001")
    aws = json.loads((project_root / "arcs/arc_001/arc_working_state.json").read_text())
    statuses = {e["state_id"]: e["status"] for e in aws["entries"]}
    assert statuses["aws_001"] == "rejected"
    assert statuses["aws_002"] == "invalidated_by_rejected_dependency"
    assert statuses["aws_003"] == "working_accepted"


def test_mark_chapters_rejected(project_root: Path):
    (project_root / "arcs/arc_001/arc_working_state.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "entries": [
                {"state_id": "aws_001", "source_chapter": "ch_001", "key": "k1", "value": "v1",
                 "status": "working_accepted", "depends_on": []},
                {"state_id": "aws_002", "source_chapter": "ch_002", "key": "k2", "value": "v2",
                 "status": "working_accepted", "depends_on": ["aws_001"]},
                {"state_id": "aws_003", "source_chapter": "ch_003", "key": "k3", "value": "v3",
                 "status": "working_accepted", "depends_on": []},
            ]
        })
    )
    mgr = ArcWorkingStateManager(project_root)
    mgr.mark_chapters_rejected("arc_001", ["ch_001"])
    aws = json.loads((project_root / "arcs/arc_001/arc_working_state.json").read_text())
    statuses = {e["state_id"]: e["status"] for e in aws["entries"]}
    assert statuses["aws_001"] == "rejected"
    assert statuses["aws_002"] == "invalidated_by_rejected_dependency"
    assert statuses["aws_003"] == "working_accepted"


def test_aws_canon_conflict_detected(project_root: Path):
    """AWS entry that contradicts canon should be detected."""
    (project_root / "canon/canon_state.json").write_text(
        json.dumps({"schema_version": "1.0", "protagonist_alive": True})
    )
    (project_root / "arcs/arc_001/arc_working_state.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "entries": [
                {"state_id": "aws_001", "source_chapter": "ch_001", "key": "protagonist_alive",
                 "value": False, "status": "working_accepted", "depends_on": []}
            ]
        })
    )
    mgr = ArcWorkingStateManager(project_root)
    conflicts = mgr.check_canon_conflict("arc_001")
    assert len(conflicts) == 1
    assert conflicts[0]["key"] == "protagonist_alive"
