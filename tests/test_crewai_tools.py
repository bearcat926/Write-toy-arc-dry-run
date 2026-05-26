import json
import pytest
from pathlib import Path
from novel_workflow.crewai.tools import write_draft, write_review, write_proposal


def test_write_draft(project_root: Path, monkeypatch):
    import novel_workflow.crewai.tools as tools_mod
    monkeypatch.setattr(tools_mod, "PROJECT_ROOT", project_root)

    path = "arcs/arc_001/drafts/ch_001.md"
    result = write_draft.run(path, "# Chapter 1\n\nThe story begins.")
    assert "Wrote" in result
    assert (project_root / path).read_text() == "# Chapter 1\n\nThe story begins."


def test_write_draft_rejects_canon(project_root: Path, monkeypatch):
    import novel_workflow.crewai.tools as tools_mod
    monkeypatch.setattr(tools_mod, "PROJECT_ROOT", project_root)

    with pytest.raises(Exception):
        write_draft.run("canon/manuscript/ch_001.md", "# Chapter 1")


def test_write_review(project_root: Path, monkeypatch):
    import novel_workflow.crewai.tools as tools_mod
    monkeypatch.setattr(tools_mod, "PROJECT_ROOT", project_root)

    path = "arcs/arc_001/reviews/ch_001_review.md"
    result = write_review.run(path, "# Review\n\nNo issues found.")
    assert "Wrote" in result


def test_write_proposal_valid_json(project_root: Path, monkeypatch):
    import novel_workflow.crewai.tools as tools_mod
    monkeypatch.setattr(tools_mod, "PROJECT_ROOT", project_root)

    proposal = {
        "schema_version": "1.0",
        "claim": "A arrives at tavern",
        "source_layer": "draft",
        "source_artifact": "arcs/arc_001/drafts/ch_001.md",
        "evidence": "A walked through the door",
        "confidence": "high",
        "target_ledger": "timeline",
        "operation": "append_event",
        "proposed_change": {"event_id": "e1", "summary": "A arrives"},
    }
    path = "arcs/arc_001/proposals/ch_001_ledger_update_proposal.json"
    result = write_proposal.run(path, json.dumps(proposal))
    assert "Wrote" in result


def test_write_proposal_rejects_invalid_json(project_root: Path, monkeypatch):
    import novel_workflow.crewai.tools as tools_mod
    monkeypatch.setattr(tools_mod, "PROJECT_ROOT", project_root)

    path = "arcs/arc_001/proposals/ch_001_ledger_update_proposal.json"
    with pytest.raises(Exception):
        write_proposal.run(path, "not json at all")
