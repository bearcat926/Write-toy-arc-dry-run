"""NarrativeGraph — deterministic derived projection of narrative structure.

Nodes represent characters, events, conflicts, foreshadows, etc.
Edges represent causal, temporal, and thematic relationships.
"""
from typing import Literal
from pydantic import field_validator
from .common import SchemaVersioned, Timestamped


class NarrativeNode(SchemaVersioned):
    """A node in the narrative graph."""
    node_id: str
    node_type: Literal[
        "character", "event", "conflict", "foreshadow",
        "promise", "emotional_residue", "world_rule", "relationship",
    ]
    label: str
    summary: str
    source_artifacts: list[str] = []
    derived: bool = True
    confidence: Literal["high", "medium", "low"] = "medium"

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("NARRATIVE_NODE_NOT_DERIVED: NarrativeNode must be derived")
        return v

    @field_validator("source_artifacts")
    @classmethod
    def must_have_sources(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("NARRATIVE_NODE_NO_SOURCES: NarrativeNode requires at least one source_artifact")
        return v


class NarrativeEdge(SchemaVersioned):
    """An edge in the narrative graph."""
    edge_id: str
    from_node: str
    to_node: str
    relation_type: Literal[
        "causes", "changes", "reveals", "blocks", "motivates",
        "foreshadows", "pays_off", "depends_on", "contradicts",
        "escalates", "resolves",
    ]
    evidence: str
    source_artifacts: list[str] = []
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("NARRATIVE_EDGE_NOT_DERIVED: NarrativeEdge must be derived")
        return v


class NarrativeGraphIndex(SchemaVersioned, Timestamped):
    """Top-level narrative graph index."""
    graph_id: str
    arc_id: str | None = None
    generated_from: list[str] = []
    nodes: list[NarrativeNode] = []
    edges: list[NarrativeEdge] = []
    derived: bool = True

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("NARRATIVE_GRAPH_NOT_DERIVED: NarrativeGraphIndex must be derived")
        return v
