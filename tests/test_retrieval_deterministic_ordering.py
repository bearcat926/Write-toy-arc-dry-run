"""Milestone 7: Retrieval deterministic ordering tests."""
import pytest
from novel_workflow.schemas.retrieval import (
    RetrievedContextItem,
    retrieval_sort_key,
)
from novel_workflow.schemas.enums import SourceLayer, RetrievalTrustLevel


def _make_item(trust, source_layer, priority, source_artifact, item_id):
    return RetrievedContextItem(
        item_id=item_id, item_type="test", content="...",
        source_layer=source_layer, source_artifact=source_artifact,
        source_artifact_hash="abc" if trust != RetrievalTrustLevel.RUNTIME_CONTEXT else None,
        is_derived=(trust == RetrievalTrustLevel.DERIVED_SUMMARY),
        trust_level=trust, priority=priority,
    )


def _canonical_item(priority=50, path="canon/approved_outline.md"):
    return _make_item(RetrievalTrustLevel.CANONICAL, SourceLayer.CANON, priority, path, f"id_{path}")


def _ledger_item(priority=40, path="ledgers/timeline.json"):
    return _make_item(RetrievalTrustLevel.LEDGER_FACT, SourceLayer.CANON, priority, path, f"id_{path}")


def _summary_item(priority=20, path="arcs/arc_001/drafts/ch_001.md"):
    return _make_item(RetrievalTrustLevel.DERIVED_SUMMARY, SourceLayer.DRAFT, priority, path, f"id_{path}")


def _runtime_item(priority=10):
    return _make_item(RetrievalTrustLevel.RUNTIME_CONTEXT, None, priority, "", "id_runtime")


def test_canonical_before_summary():
    items = [_summary_item(), _canonical_item()]
    sorted_items = sorted(items, key=retrieval_sort_key)
    assert sorted_items[0].trust_level == RetrievalTrustLevel.CANONICAL


def test_ledger_before_working_state():
    ws = _make_item(RetrievalTrustLevel.WORKING_STATE, SourceLayer.ARC_WORKING_STATE, 40, "arcs/arc_001/arc_working_state.json", "id_ws")
    items = [ws, _ledger_item()]
    sorted_items = sorted(items, key=retrieval_sort_key)
    assert sorted_items[0].trust_level == RetrievalTrustLevel.LEDGER_FACT


def test_runtime_context_last():
    items = [_runtime_item(), _summary_item(), _canonical_item()]
    sorted_items = sorted(items, key=retrieval_sort_key)
    assert sorted_items[-1].trust_level == RetrievalTrustLevel.RUNTIME_CONTEXT


def test_same_trust_by_priority():
    c1 = _canonical_item(priority=50, path="canon/a.md")
    c2 = _canonical_item(priority=80, path="canon/b.md")
    items = [c1, c2]
    sorted_items = sorted(items, key=retrieval_sort_key)
    assert sorted_items[0].priority == 80


def test_same_priority_by_path():
    c1 = _canonical_item(priority=50, path="canon/z.md")
    c2 = _canonical_item(priority=50, path="canon/a.md")
    items = [c1, c2]
    sorted_items = sorted(items, key=retrieval_sort_key)
    assert sorted_items[0].source_artifact == "canon/a.md"


def test_deterministic_output():
    """Same input must always produce same output regardless of insertion order."""
    items_a = [_summary_item(), _canonical_item(), _ledger_item(), _runtime_item()]
    items_b = list(reversed(items_a))

    sorted_a = sorted(items_a, key=retrieval_sort_key)
    sorted_b = sorted(items_b, key=retrieval_sort_key)

    assert [i.item_id for i in sorted_a] == [i.item_id for i in sorted_b]


def test_10_runs_deterministic():
    """Run sort 10 times — output must be identical."""
    items = [_summary_item(), _canonical_item(), _ledger_item(), _runtime_item()]
    results = []
    for _ in range(10):
        sorted_items = sorted(items, key=retrieval_sort_key)
        results.append([i.item_id for i in sorted_items])
    assert all(r == results[0] for r in results)


def test_path_normalization_in_sort():
    """Windows backslash paths should sort same as forward slash."""
    item_bslash = _canonical_item(path="canon\\test.md")
    item_fslash = _canonical_item(path="canon/test.md")
    key1 = retrieval_sort_key(item_bslash)
    key2 = retrieval_sort_key(item_fslash)
    # The sort key should normalize paths
    assert key1[3] == key2[3]
