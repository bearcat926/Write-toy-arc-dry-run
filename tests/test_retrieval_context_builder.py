"""RetrievalContextBuilder tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.schemas.retrieval import RetrievalRequest
from novel_workflow.schemas.enums import ContextBuilderMode


def _seed_project(root: Path):
    """Create minimal project with canon, contract, and summaries."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text(
        "# Outline\n\nA story about adventure.", encoding="utf-8"
    )
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Arc Contract\n\nGoal: Hero's journey.", encoding="utf-8"
    )
    (root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "summaries" / "ch_001_summary.json").write_text(
        json.dumps({
            "chapter_id": "ch_001",
            "arc_id": "arc_001",
            "source_layer": "draft",
            "source_artifact": "arcs/arc_001/drafts/ch_001.md",
            "source_artifact_hash": "abc123",
            "causal_events": ["Hero departs"],
            "character_state_changes": [{"character": "Hero", "change": "embarked"}],
            "retrieval_tags": ["departure"],
            "derived": True,
        }),
        encoding="utf-8",
    )


def test_build_returns_context_and_trace(tmp_path: Path):
    _seed_project(tmp_path)
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(arc_id="arc_001", chapter_id="ch_002", agent_role="writer")
    context, trace = builder.build(request)
    assert isinstance(context, str)
    assert len(context) > 0
    assert trace.context_builder_mode == ContextBuilderMode.RETRIEVAL
    assert trace.derived is True
    assert trace.request.agent_role == "writer"


def test_build_includes_canon_and_summary(tmp_path: Path):
    _seed_project(tmp_path)
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(arc_id="arc_001", chapter_id="ch_002", agent_role="writer")
    context, trace = builder.build(request)
    assert "Story outline" in context or "adventure" in context
    assert len(trace.selected_items) >= 2  # outline + contract + summary


def test_budget_enforcement(tmp_path: Path):
    _seed_project(tmp_path)
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_002",
        agent_role="writer", max_character_budget=50,
    )
    context, trace = builder.build(request)
    assert len(context) <= 50 + 50  # some margin for headers
    assert len(trace.dropped_items) > 0
    assert trace.dropped_items[0]["drop_reason"] == "budget_exceeded"


def test_all_selected_have_source(tmp_path: Path):
    _seed_project(tmp_path)
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(arc_id="arc_001", chapter_id="ch_002", agent_role="writer")
    _, trace = builder.build(request)
    for item in trace.selected_items:
        assert item.source_artifact, f"item {item.item_id} missing source_artifact"


def test_missing_sources_handled(tmp_path: Path):
    """Builder should not crash when no sources exist."""
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(arc_id="arc_001", chapter_id="ch_001", agent_role="writer")
    context, trace = builder.build(request)
    assert "(no context available)" in context
    assert len(trace.selected_items) == 0


def test_current_chapter_summary_excluded(tmp_path: Path):
    """Current chapter's summary should not be included in context."""
    _seed_project(tmp_path)
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(arc_id="arc_001", chapter_id="ch_001", agent_role="writer")
    _, trace = builder.build(request)
    for item in trace.selected_items:
        assert "ch_001_summary" not in item.item_id
