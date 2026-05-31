"""30 chapter stress test — validates context growth control.

Uses deterministic fake-agent fixture.
"""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.narrative_compressor import NarrativeCompressor
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.schemas.retrieval import RetrievalRequest


def _seed_project(root: Path, chapters: int = 30):
    """Create project with many chapters."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text(
        "# Outline\n\n" + "Adventure story content. " * 50,
        encoding="utf-8",
    )
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Contract\nGoal: Complete journey.\n" * 20,
        encoding="utf-8",
    )
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(
            f"# Chapter {i}\n\n" + f"Content of chapter {i}. " * 30 + "\n",
            encoding="utf-8",
        )


def test_stress_30_chapters_context_bounded(tmp_path: Path):
    """Context should not grow unboundedly across 30 chapters."""
    _seed_project(tmp_path, chapters=30)
    compressor = NarrativeCompressor(tmp_path)

    # Generate summaries for first 29 chapters
    for i in range(1, 30):
        compressor.compress("arc_001", f"ch_{i:03d}")

    # Build context for chapter 30
    builder = RetrievalContextBuilder(tmp_path)
    request = RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_030",
        agent_role="writer", max_character_budget=35000,
    )
    context, trace = builder.build(request)

    # Context should be bounded
    assert len(context) <= 35000 + 1000  # margin for headers
    assert trace.final_character_count <= 35000 + 1000

    # All selected items should have source
    for item in trace.selected_items:
        assert item.source_artifact


def test_stress_30_chapters_summaries_generated(tmp_path: Path):
    """Each chapter should produce a summary."""
    _seed_project(tmp_path, chapters=30)
    compressor = NarrativeCompressor(tmp_path)

    for i in range(1, 31):
        summary = compressor.compress("arc_001", f"ch_{i:03d}")
        assert summary.chapter_id == f"ch_{i:03d}"
        assert summary.derived is True

    # All summaries should exist
    for i in range(1, 31):
        path = tmp_path / "workspace" / "summaries" / f"ch_{i:03d}_summary.json"
        assert path.exists()


def test_stress_30_chapters_traces_written(tmp_path: Path):
    """Each chapter should produce a retrieval trace in active mode."""
    _seed_project(tmp_path, chapters=30)
    provider = ContextProvider(tmp_path, mode="retrieval_active")

    for i in range(1, 31):
        _, trace = provider.build_writer_context("arc_001", i)
        assert trace is not None
        ContextProvider.write_trace(tmp_path, "arc_001", f"ch_{i:03d}", trace)

    # All traces should exist
    for i in range(1, 31):
        path = tmp_path / "workspace" / "retrieval_traces" / "arc_001" / f"ch_{i:03d}" / "writer.jsonl"
        assert path.exists()


def test_stress_30_context_growth_sublinear(tmp_path: Path):
    """Context size at chapter 30 should not be 30x chapter 1."""
    _seed_project(tmp_path, chapters=30)
    compressor = NarrativeCompressor(tmp_path)

    for i in range(1, 31):
        compressor.compress("arc_001", f"ch_{i:03d}")

    builder = RetrievalContextBuilder(tmp_path)

    # Context at chapter 1
    _, trace1 = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_001", agent_role="writer", max_character_budget=35000,
    ))

    # Context at chapter 30
    _, trace30 = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_030", agent_role="writer", max_character_budget=35000,
    ))

    # Growth should be sublinear
    if trace1.final_character_count > 0:
        growth_ratio = trace30.final_character_count / trace1.final_character_count
        assert growth_ratio < 10.0, f"Context growth too high: {growth_ratio}x"
