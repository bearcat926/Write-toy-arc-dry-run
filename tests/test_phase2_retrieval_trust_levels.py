"""Phase 2 RetrievalTrustLevel extension tests."""
import pytest
from novel_workflow.schemas.enums import RetrievalTrustLevel
from novel_workflow.schemas.retrieval import (
    TRUST_LEVEL_PRIORITY,
    TRUST_LEVEL_SOURCE_LAYER_MAP,
    HASH_REQUIRED_TRUST_LEVELS,
)


def test_all_trust_levels_have_priority():
    for level in RetrievalTrustLevel:
        assert level in TRUST_LEVEL_PRIORITY, f"Missing priority for {level}"


def test_all_trust_levels_have_source_layer_map():
    for level in RetrievalTrustLevel:
        assert level in TRUST_LEVEL_SOURCE_LAYER_MAP, f"Missing mapping for {level}"


def test_derived_levels_have_none_source_layer():
    derived_levels = [
        RetrievalTrustLevel.DERIVED_GRAPH,
        RetrievalTrustLevel.DERIVED_LIFECYCLE,
        RetrievalTrustLevel.DERIVED_DRIFT,
        RetrievalTrustLevel.DERIVED_ARC_PLAN,
    ]
    for level in derived_levels:
        assert TRUST_LEVEL_SOURCE_LAYER_MAP[level] is None, f"{level} should map to None"


def test_derived_priority_ordering():
    p = TRUST_LEVEL_PRIORITY
    assert p[RetrievalTrustLevel.DERIVED_SUMMARY] > p[RetrievalTrustLevel.DERIVED_GRAPH]
    assert p[RetrievalTrustLevel.DERIVED_GRAPH] > p[RetrievalTrustLevel.DERIVED_LIFECYCLE]
    assert p[RetrievalTrustLevel.DERIVED_LIFECYCLE] > p[RetrievalTrustLevel.DERIVED_DRIFT]
    assert p[RetrievalTrustLevel.DERIVED_DRIFT] > p[RetrievalTrustLevel.DERIVED_ARC_PLAN]
    assert p[RetrievalTrustLevel.DERIVED_ARC_PLAN] > p[RetrievalTrustLevel.RUNTIME_CONTEXT]


def test_derived_levels_not_in_hash_required():
    derived_levels = [
        RetrievalTrustLevel.DERIVED_GRAPH,
        RetrievalTrustLevel.DERIVED_LIFECYCLE,
        RetrievalTrustLevel.DERIVED_DRIFT,
        RetrievalTrustLevel.DERIVED_ARC_PLAN,
    ]
    for level in derived_levels:
        assert level not in HASH_REQUIRED_TRUST_LEVELS, f"{level} should not require hash"
