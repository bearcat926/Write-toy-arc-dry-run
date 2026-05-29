"""Phase 2 retrieval schema baseline tests.

Verifies current schema structure is stable before Phase 2 extensions.
"""
import pytest
from novel_workflow.schemas.retrieval import (
    RetrievalRequest,
    RetrievedContextItem,
    RetrievalTrace,
    retrieval_sort_key,
    TRUST_LEVEL_PRIORITY,
    SOURCE_LAYER_PRIORITY,
    TRUST_LEVEL_SOURCE_LAYER_MAP,
    HASH_REQUIRED_TRUST_LEVELS,
)
from novel_workflow.schemas.enums import (
    RetrievalTrustLevel,
    RetrievalFallbackReason,
    ContextBuilderMode,
    ProtocolVersion,
    SourceLayer,
)


def test_retrieval_request_instantiation():
    req = RetrievalRequest(arc_id="arc_001", chapter_id="ch_001", agent_role="writer")
    assert req.arc_id == "arc_001"
    assert req.max_character_budget == 12000


def test_retrieved_context_item_instantiation():
    item = RetrievedContextItem(
        item_id="test_1",
        item_type="summary",
        content="test content",
        trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
        is_derived=True,
        source_layer=SourceLayer.DRAFT,
    )
    assert item.item_id == "test_1"
    assert item.is_derived is True


def test_retrieval_trace_instantiation():
    req = RetrievalRequest(arc_id="arc_001", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=req)
    assert trace.derived is True
    assert trace.fallback_used is False


def test_retrieval_sort_key_deterministic():
    item = RetrievedContextItem(
        item_id="test_1",
        item_type="summary",
        content="test",
        trust_level=RetrievalTrustLevel.CANONICAL,
        source_layer=SourceLayer.CANON,
        source_artifact_hash="abc123",
    )
    key1 = retrieval_sort_key(item)
    key2 = retrieval_sort_key(item)
    assert key1 == key2


def test_trust_level_priority_complete():
    for level in RetrievalTrustLevel:
        assert level in TRUST_LEVEL_PRIORITY, f"Missing priority for {level}"


def test_trust_level_source_layer_map_complete():
    for level in RetrievalTrustLevel:
        assert level in TRUST_LEVEL_SOURCE_LAYER_MAP, f"Missing mapping for {level}"


def test_fallback_reason_enum():
    assert hasattr(RetrievalFallbackReason, "SUMMARY_MISSING")
    assert hasattr(RetrievalFallbackReason, "TRACE_WRITE_FAILED")


def test_context_builder_mode_enum():
    assert hasattr(ContextBuilderMode, "LEGACY")
    assert hasattr(ContextBuilderMode, "RETRIEVAL")


def test_protocol_version_enum():
    assert hasattr(ProtocolVersion, "PHASE2_V1")
