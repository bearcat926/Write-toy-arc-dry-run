"""NarrativeGraphBuilder tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.narrative_graph_builder import NarrativeGraphBuilder


def _seed_project(root: Path):
    """Create project with ledgers and summaries."""
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(json.dumps({
        "schema_version": "1.0",
        "events": [
            {"event_id": "e1", "summary": "Hero departs", "participants": ["hero"]},
            {"event_id": "e2", "summary": "Hero arrives", "participants": ["hero", "villain"]},
        ],
    }), encoding="utf-8")
    (root / "ledgers" / "character_knowledge.json").write_text(json.dumps({
        "schema_version": "1.0",
        "character_knowledge_entries": [
            {"character_id": "hero", "knowledge": "knows the way"},
            {"character_id": "villain", "knowledge": "lurks in shadows"},
        ],
    }), encoding="utf-8")
    (root / "ledgers" / "foreshadowing.json").write_text(json.dumps({
        "schema_version": "1.0",
        "foreshadowing_entries": [
            {"foreshadow_id": "fs1", "summary": "Broken sword", "status": "introduced"},
        ],
    }), encoding="utf-8")
    (root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "summaries" / "ch_001_summary.json").write_text(json.dumps({
        "chapter_id": "ch_001", "arc_id": "arc_001",
        "source_layer": "draft", "source_artifact": "arcs/arc_001/drafts/ch_001.md",
        "source_artifact_hash": "abc", "derived": True,
        "causal_events": ["Hero leaves home"],
        "emotional_residue": [{"emotion": "fear", "intensity": "high"}],
        "foreshadow_updates": ["fs1 activated"],
    }), encoding="utf-8")


def test_build_from_ledgers(tmp_path: Path):
    _seed_project(tmp_path)
    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.build(arc_id="arc_001")
    assert graph.derived is True
    assert graph.arc_id == "arc_001"
    assert len(graph.nodes) > 0
    # Should have event nodes, character nodes, foreshadow nodes
    node_types = {n.node_type for n in graph.nodes}
    assert "event" in node_types
    assert "character" in node_types
    assert "foreshadow" in node_types


def test_build_includes_summary_nodes(tmp_path: Path):
    _seed_project(tmp_path)
    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.build()
    node_types = {n.node_type for n in graph.nodes}
    assert "emotional_residue" in node_types


def test_build_empty_ledgers(tmp_path: Path):
    (tmp_path / "ledgers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []}), encoding="utf-8"
    )
    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.build()
    assert graph.derived is True
    assert len(graph.nodes) == 0


def test_build_participant_edges(tmp_path: Path):
    _seed_project(tmp_path)
    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.build()
    # Should have edges from hero/villain to events
    assert len(graph.edges) > 0
