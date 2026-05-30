"""NarrativeGraph schema tests."""
import json
import pytest
from novel_workflow.schemas.narrative_graph import (
    NarrativeNode, NarrativeEdge, NarrativeGraphIndex,
)


def test_node_instantiation():
    node = NarrativeNode(
        node_id="n1", node_type="character", label="Hero",
        summary="Main character", source_artifacts=["drafts/ch_001.md"],
    )
    assert node.derived is True
    assert node.confidence == "medium"


def test_node_must_be_derived():
    with pytest.raises(ValueError, match="NARRATIVE_NODE_NOT_DERIVED"):
        NarrativeNode(
            node_id="n1", node_type="character", label="Hero",
            summary="Main character", source_artifacts=["drafts/ch_001.md"],
            derived=False,
        )


def test_node_must_have_sources():
    with pytest.raises(ValueError, match="NARRATIVE_NODE_NO_SOURCES"):
        NarrativeNode(
            node_id="n1", node_type="character", label="Hero",
            summary="Main character", source_artifacts=[],
        )


def test_edge_instantiation():
    edge = NarrativeEdge(
        edge_id="e1", from_node="n1", to_node="n2",
        relation_type="causes", evidence="A leads to B",
        source_artifacts=["drafts/ch_001.md"],
    )
    assert edge.derived is True


def test_edge_must_be_derived():
    with pytest.raises(ValueError, match="NARRATIVE_EDGE_NOT_DERIVED"):
        NarrativeEdge(
            edge_id="e1", from_node="n1", to_node="n2",
            relation_type="causes", evidence="test",
            source_artifacts=["drafts/ch_001.md"],
            derived=False,
        )


def test_graph_index_instantiation():
    graph = NarrativeGraphIndex(
        graph_id="g1", arc_id="arc_001",
        generated_from=["summaries/ch_001.json"],
        nodes=[
            NarrativeNode(node_id="n1", node_type="event", label="E1",
                          summary="Event 1", source_artifacts=["drafts/ch_001.md"]),
        ],
        edges=[],
    )
    assert graph.derived is True
    assert len(graph.nodes) == 1


def test_graph_serialization():
    graph = NarrativeGraphIndex(
        graph_id="g1", arc_id="arc_001",
        nodes=[NarrativeNode(node_id="n1", node_type="event", label="E1",
                              summary="Event 1", source_artifacts=["drafts/ch_001.md"])],
        edges=[NarrativeEdge(edge_id="e1", from_node="n1", to_node="n1",
                              relation_type="resolves", evidence="self-resolve",
                              source_artifacts=["drafts/ch_001.md"])],
    )
    data = json.loads(graph.model_dump_json())
    assert data["derived"] is True
    assert len(data["nodes"]) == 1
    assert len(data["edges"]) == 1
