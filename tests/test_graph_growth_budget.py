"""Graph growth budget tests."""
import pytest
from novel_workflow.schemas.narrative_graph import NarrativeNode, NarrativeEdge, NarrativeGraphIndex
from novel_workflow.system_scripts.narrative_graph_builder import NarrativeGraphBuilder


def _make_graph(node_count: int, edge_count: int) -> NarrativeGraphIndex:
    nodes = [
        NarrativeNode(node_id=f"n{i}", node_type="event", label=f"E{i}",
                       summary=f"Event {i}", source_artifacts=["test.md"])
        for i in range(node_count)
    ]
    edges = [
        NarrativeEdge(edge_id=f"e{i}", from_node=f"n{i % max(node_count, 1)}",
                       to_node=f"n{(i+1) % max(node_count, 1)}",
                       relation_type="causes", evidence="test", source_artifacts=["test.md"])
        for i in range(edge_count)
    ]
    return NarrativeGraphIndex(graph_id="test", nodes=nodes, edges=edges)


def test_budget_within_limits():
    graph = _make_graph(100, 500)
    report = NarrativeGraphBuilder.check_budget(graph)
    assert report["budget_exceeded"] is False
    assert len(report["warnings"]) == 0


def test_budget_nodes_exceeded():
    graph = _make_graph(501, 100)
    report = NarrativeGraphBuilder.check_budget(graph)
    assert report["budget_exceeded"] is True
    assert any("node_count" in w for w in report["warnings"])


def test_budget_edges_exceeded():
    graph = _make_graph(100, 2001)
    report = NarrativeGraphBuilder.check_budget(graph)
    assert report["budget_exceeded"] is True
    assert any("edge_count" in w for w in report["warnings"])


def test_budget_exact_limits():
    graph = _make_graph(500, 2000)
    report = NarrativeGraphBuilder.check_budget(graph)
    assert report["budget_exceeded"] is False


def test_budget_report_schema():
    graph = _make_graph(10, 20)
    report = NarrativeGraphBuilder.check_budget(graph)
    assert "node_count" in report
    assert "edge_count" in report
    assert "max_nodes" in report
    assert "max_edges" in report
    assert "budget_exceeded" in report
    assert "warnings" in report
