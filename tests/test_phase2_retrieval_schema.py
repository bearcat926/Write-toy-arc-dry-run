"""Phase 2 retrieval schema extension tests."""
import pytest
from pydantic import ValidationError
from novel_workflow.schemas.retrieval import (
    RetrievalRequest,
    RetrievedContextItem,
    RetrievalTrace,
)
from novel_workflow.schemas.enums import (
    RetrievalTrustLevel,
    ContextBuilderMode,
    SourceLayer,
)


def test_retrieval_trace_new_fields_defaults():
    req = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=req)
    assert trace.generation_id == ""
    assert trace.context_mode == ContextBuilderMode.LEGACY
    assert trace.trace_write_status == "written"
    assert trace.trace_write_error is None
    assert trace.ranking_features == {}


def test_retrieval_trace_with_generation_id():
    req = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=req, generation_id="gen-123", context_mode=ContextBuilderMode.RETRIEVAL)
    assert trace.generation_id == "gen-123"
    assert trace.context_mode == ContextBuilderMode.RETRIEVAL


def test_trace_write_failed_requires_error():
    req = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    with pytest.raises(ValidationError, match="trace_write_error"):
        RetrievalTrace(request=req, trace_write_status="failed", trace_write_error=None)


def test_trace_write_failed_with_error():
    req = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=req, trace_write_status="failed", trace_write_error="disk full")
    assert trace.trace_write_status == "failed"
    assert trace.trace_write_error == "disk full"


def test_retrieved_context_item_selection_reason():
    item = RetrievedContextItem(
        item_id="t1", item_type="summary", content="test",
        trust_level=RetrievalTrustLevel.DERIVED_SUMMARY, is_derived=True,
        source_layer=SourceLayer.DRAFT, selection_reason="score_top10",
    )
    assert item.selection_reason == "score_top10"


def test_derived_graph_trust_level():
    item = RetrievedContextItem(
        item_id="g1", item_type="graph", content="graph data",
        trust_level=RetrievalTrustLevel.DERIVED_GRAPH, is_derived=True,
    )
    assert item.trust_level == RetrievalTrustLevel.DERIVED_GRAPH
    assert item.is_derived is True


def test_derived_graph_rejects_not_derived():
    with pytest.raises(ValidationError, match="is_derived"):
        RetrievedContextItem(
            item_id="g1", item_type="graph", content="data",
            trust_level=RetrievalTrustLevel.DERIVED_GRAPH, is_derived=False,
        )
