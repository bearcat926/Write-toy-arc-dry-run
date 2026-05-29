"""Phase 2 ranking contract determinism tests."""
from novel_workflow.schemas.retrieval import (
    RetrievedContextItem,
    retrieval_sort_key,
)
from novel_workflow.schemas.enums import RetrievalTrustLevel, SourceLayer


def test_sort_key_deterministic():
    items = [
        RetrievedContextItem(item_id="a", item_type="s", content="c",
                             trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
                             is_derived=True, source_layer=SourceLayer.DRAFT),
        RetrievedContextItem(item_id="b", item_type="s", content="c",
                             trust_level=RetrievalTrustLevel.CANONICAL,
                             source_layer=SourceLayer.CANON,
                             source_artifact_hash="h"),
    ]
    result1 = [retrieval_sort_key(i) for i in items]
    result2 = [retrieval_sort_key(i) for i in items]
    result3 = [retrieval_sort_key(i) for i in items]
    assert result1 == result2 == result3


def test_sort_ordering_by_trust_level():
    canonical = RetrievedContextItem(
        item_id="c", item_type="s", content="c",
        trust_level=RetrievalTrustLevel.CANONICAL,
        source_layer=SourceLayer.CANON, source_artifact_hash="h")
    derived = RetrievedContextItem(
        item_id="d", item_type="s", content="c",
        trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
        is_derived=True, source_layer=SourceLayer.DRAFT)
    assert retrieval_sort_key(canonical) < retrieval_sort_key(derived)


def test_sort_ordering_among_derived():
    summary = RetrievedContextItem(
        item_id="s", item_type="s", content="c",
        trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
        is_derived=True, source_layer=SourceLayer.DRAFT)
    graph = RetrievedContextItem(
        item_id="g", item_type="s", content="c",
        trust_level=RetrievalTrustLevel.DERIVED_GRAPH,
        is_derived=True)
    assert retrieval_sort_key(summary) < retrieval_sort_key(graph)
