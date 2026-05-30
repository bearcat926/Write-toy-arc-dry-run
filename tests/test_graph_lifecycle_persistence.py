"""Graph/Lifecycle persistence and growth budget tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.narrative_graph_builder import NarrativeGraphBuilder
from novel_workflow.system_scripts.foreshadow_lifecycle_manager import ForeshadowLifecycleManager


def _seed_project(root: Path):
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": [
            {"event_id": "e1", "summary": "Alice arrives", "chapter_id": "ch_001"}
        ]}), encoding="utf-8"
    )
    (root / "ledgers" / "character_knowledge.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
    )
    (root / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "foreshadowing_entries": [
            {"foreshadow_id": "fs1", "summary": "Broken sword", "status": "introduced", "chapter_id": "ch_001"}
        ]}), encoding="utf-8"
    )
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract\n", encoding="utf-8")


def test_graph_write_index(tmp_path: Path):
    _seed_project(tmp_path)
    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.write_index("arc_001")
    output = tmp_path / "workspace" / "narrative_graph_index.json"
    assert output.exists()
    data = json.loads(output.read_text())
    assert data["arc_id"] == "arc_001"


def test_lifecycle_write_index(tmp_path: Path):
    _seed_project(tmp_path)
    manager = ForeshadowLifecycleManager(tmp_path)
    index, transitions = manager.write_index("arc_001")
    output = tmp_path / "workspace" / "foreshadow_lifecycle_index.json"
    assert output.exists()
    data = json.loads(output.read_text())
    assert len(data["items"]) >= 1


def test_graph_budget_within_limits(tmp_path: Path):
    _seed_project(tmp_path)
    builder = NarrativeGraphBuilder(tmp_path)
    graph = builder.build("arc_001")
    budget = NarrativeGraphBuilder.check_budget(graph)
    assert budget["budget_exceeded"] is False


def test_graph_budget_exceeded():
    """Graph with too many nodes should be detected."""
    from novel_workflow.schemas.narrative_graph import NarrativeNode
    nodes = [
        NarrativeNode(node_id=f"n{i}", node_type="event", label=f"N{i}", summary="s")
        for i in range(501)
    ]
    from novel_workflow.schemas.narrative_graph import NarrativeGraphIndex
    graph = NarrativeGraphIndex(
        graph_id="test", generated_from=[], nodes=nodes, edges=[],
    )
    budget = NarrativeGraphBuilder.check_budget(graph)
    assert budget["budget_exceeded"] is True
    assert "node_count" in budget["warnings"][0]
