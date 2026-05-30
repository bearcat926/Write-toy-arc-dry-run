"""Phase 2 long arc context stress tests.

Validates that context growth is controlled across multiple chapters.
Uses deterministic fake-agent fixture, no LLM required.
"""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.narrative_compressor import NarrativeCompressor
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.schemas.retrieval import RetrievalRequest


def _seed_project(root: Path, chapters: int = 10):
    """Create project with multiple chapters."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text(
        "# Outline\n\nAn epic adventure spanning many chapters.\n" * 10,
        encoding="utf-8",
    )
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Contract\n\nGoal: Complete hero's journey.\n" * 5,
        encoding="utf-8",
    )
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(
            f"# Chapter {i}\n\n{'Content of chapter ' + str(i) + '. ' * 20}\n",
            encoding="utf-8",
        )


def test_stress_10_chapters_context_bounded(tmp_path: Path):
    """Context should not grow unboundedly across 10 chapters."""
    _seed_project(tmp_path, chapters=10)
    compressor = NarrativeCompressor(tmp_path)

    # Generate summaries for first 9 chapters
    for i in range(1, 10):
        compressor.compress("arc_001", f"ch_{i:03d}")

    # Build context for chapter 10
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_010",
        agent_role="writer", max_character_budget=25000,
    )
    context, trace = builder.build(request)

    # Context should be bounded
    assert len(context) <= 25000 + 500  # margin for headers
    assert trace.final_character_count <= 25000 + 500

    # All selected items should have source
    for item in trace.selected_items:
        assert item.source_artifact


def test_stress_10_chapters_summaries_generated(tmp_path: Path):
    """Each chapter should produce a summary."""
    _seed_project(tmp_path, chapters=10)
    compressor = NarrativeCompressor(tmp_path)

    for i in range(1, 11):
        summary = compressor.compress("arc_001", f"ch_{i:03d}")
        assert summary.chapter_id == f"ch_{i:03d}"
        assert summary.derived is True

    # All summaries should exist
    for i in range(1, 11):
        path = tmp_path / "workspace" / "summaries" / f"ch_{i:03d}_summary.json"
        assert path.exists()


def test_stress_10_chapters_traces_written(tmp_path: Path):
    """Each chapter should produce a retrieval trace in active mode."""
    _seed_project(tmp_path, chapters=10)
    provider = ContextProvider(tmp_path, mode="retrieval_active")

    for i in range(1, 11):
        _, trace = provider.build_writer_context("arc_001", i)
        assert trace is not None
        ContextProvider.write_trace(tmp_path, "arc_001", f"ch_{i:03d}", trace)

    # All traces should exist
    for i in range(1, 11):
        path = tmp_path / "workspace" / "retrieval_traces" / f"ch_{i:03d}.jsonl"
        assert path.exists()


def test_stress_context_growth_sublinear(tmp_path: Path):
    """Context size at chapter 10 should not be 10x chapter 1."""
    _seed_project(tmp_path, chapters=10)
    compressor = NarrativeCompressor(tmp_path)

    for i in range(1, 11):
        compressor.compress("arc_001", f"ch_{i:03d}")

    builder = RetrievalContextBuilder(tmp_path)

    # Context at chapter 1
    _, trace1 = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_001", agent_role="writer", max_character_budget=25000,
    ))

    # Context at chapter 10
    _, trace10 = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_010", agent_role="writer", max_character_budget=25000,
    ))

    # Growth should be sublinear (ch_010 includes ch_001 summaries, but budget caps it)
    # ch_010 should not be 10x ch_001
    if trace1.final_character_count > 0:
        growth_ratio = trace10.final_character_count / trace1.final_character_count
        assert growth_ratio < 5.0, f"Context growth too high: {growth_ratio}x"
