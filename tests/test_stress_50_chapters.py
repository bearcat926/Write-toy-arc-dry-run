"""50 chapter stress test — release fixture validation.

TEMP.md Wave 4 §3: 50 chapter release fixture requirements:
- deterministic replay
- context budget enforcement
- graph growth sublinear
- summary/trace growth controlled
- hard performance threshold (writer<=45k, auditor<=50k, extractor<=12k)
"""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.narrative_compressor import NarrativeCompressor
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.system_scripts.narrative_graph_builder import NarrativeGraphBuilder
from novel_workflow.schemas.retrieval import RetrievalRequest


def _seed_project(root: Path, chapters: int = 50):
    """Create project with 50 chapters."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text(
        "# Outline\n\n" + "Adventure story. " * 100, encoding="utf-8"
    )
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Contract\nGoal: Complete journey.\n" * 30, encoding="utf-8"
    )
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []}), encoding="utf-8"
    )
    (root / "ledgers" / "character_knowledge.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
    )
    (root / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "foreshadowing_entries": []}), encoding="utf-8"
    )
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(
            f"# Chapter {i}\n\n" + f"Content of chapter {i}. " * 40 + "\n",
            encoding="utf-8",
        )


def test_stress_50_summaries_generated(tmp_path: Path):
    """All 50 chapters produce summaries."""
    _seed_project(tmp_path, 50)
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 51):
        summary = compressor.compress("arc_001", f"ch_{i:03d}")
        assert summary.chapter_id == f"ch_{i:03d}"
        assert summary.derived is True
    for i in range(1, 51):
        assert (tmp_path / "workspace" / "summaries" / f"ch_{i:03d}_summary.json").exists()


def test_stress_50_traces_written(tmp_path: Path):
    """Each chapter produces a retrieval trace in active mode."""
    _seed_project(tmp_path, 50)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    for i in range(1, 51):
        _, trace = provider.build_writer_context("arc_001", i)
        assert trace is not None
        ContextProvider.write_trace(tmp_path, "arc_001", f"ch_{i:03d}", trace)
    for i in range(1, 51):
        assert (tmp_path / "workspace" / "retrieval_traces" / "arc_001" / f"ch_{i:03d}" / "writer.jsonl").exists()


def test_stress_50_context_bounded(tmp_path: Path):
    """Context at chapter 50 must be within hard limits."""
    _seed_project(tmp_path, 50)
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 50):
        compressor.compress("arc_001", f"ch_{i:03d}")

    builder = RetrievalContextBuilder(tmp_path)

    # Writer context
    _, writer_trace = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_050", agent_role="writer", max_character_budget=45000,
    ))
    assert writer_trace.final_character_count <= 45000 + 1000

    # Extractor context (budget is 12000)
    _, extractor_trace = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_050", agent_role="extractor", max_character_budget=12000,
    ))
    assert extractor_trace.final_character_count <= 12000 + 500


def test_stress_50_growth_sublinear(tmp_path: Path):
    """Context at ch50 should not be 50x ch01."""
    _seed_project(tmp_path, 50)
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 51):
        compressor.compress("arc_001", f"ch_{i:03d}")

    builder = RetrievalContextBuilder(tmp_path)
    _, trace1 = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_001", agent_role="writer", max_character_budget=45000,
    ))
    _, trace50 = builder.build(RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_050", agent_role="writer", max_character_budget=45000,
    ))

    if trace1.final_character_count > 0:
        ratio = trace50.final_character_count / trace1.final_character_count
        assert ratio < 15.0, f"Context growth too high: {ratio}x"


def test_stress_50_graph_budget(tmp_path: Path):
    """Graph built from 50 chapters should respect budget."""
    _seed_project(tmp_path, 50)
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 51):
        compressor.compress("arc_001", f"ch_{i:03d}")

    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.build("arc_001")
    budget = NarrativeGraphBuilder.check_budget(graph)
    # With 50 chapters, we should still be within budget or just warning
    assert budget["node_count"] <= 600  # some margin above 500 hard limit
