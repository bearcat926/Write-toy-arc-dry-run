"""Milestone 6: Retrieval trust matrix tests."""
import pytest
from novel_workflow.schemas.retrieval import RetrievedContextItem
from novel_workflow.schemas.enums import SourceLayer, RetrievalTrustLevel


def test_canonical_with_canon_layer():
    item = RetrievedContextItem(
        item_id="test1", item_type="canon_outline", content="...",
        source_layer=SourceLayer.CANON, source_artifact="canon/approved_outline.md",
        source_artifact_hash="abc123",
        is_derived=False, trust_level=RetrievalTrustLevel.CANONICAL,
    )
    assert item.trust_level == RetrievalTrustLevel.CANONICAL


def test_canonical_with_draft_layer_rejected():
    with pytest.raises(ValueError, match="requires source_layer=canon"):
        RetrievedContextItem(
            item_id="test1", item_type="canon", content="...",
            source_layer=SourceLayer.DRAFT, source_artifact="arcs/arc_001/drafts/ch_001.md",
            source_artifact_hash="abc123",
            is_derived=False, trust_level=RetrievalTrustLevel.CANONICAL,
        )


def test_canonical_without_hash_rejected():
    with pytest.raises(ValueError, match="requires source_artifact_hash"):
        RetrievedContextItem(
            item_id="test1", item_type="canon", content="...",
            source_layer=SourceLayer.CANON, source_artifact="canon/approved_outline.md",
            is_derived=False, trust_level=RetrievalTrustLevel.CANONICAL,
        )


def test_ledger_fact_requires_hash():
    with pytest.raises(ValueError, match="requires source_artifact_hash"):
        RetrievedContextItem(
            item_id="test1", item_type="event", content="...",
            source_layer=SourceLayer.CANON, source_artifact="ledgers/timeline.json",
            is_derived=False, trust_level=RetrievalTrustLevel.LEDGER_FACT,
        )


def test_working_state_with_correct_layer():
    item = RetrievedContextItem(
        item_id="test1", item_type="aws", content="...",
        source_layer=SourceLayer.ARC_WORKING_STATE,
        source_artifact="arcs/arc_001/arc_working_state.json",
        source_artifact_hash="abc123",
        is_derived=False, trust_level=RetrievalTrustLevel.WORKING_STATE,
    )
    assert item.trust_level == RetrievalTrustLevel.WORKING_STATE


def test_derived_summary_with_draft_layer():
    item = RetrievedContextItem(
        item_id="test1", item_type="summary", content="...",
        source_layer=SourceLayer.DRAFT,
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        is_derived=True, trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
    )
    assert item.is_derived is True


def test_derived_summary_must_be_derived():
    with pytest.raises(ValueError, match="is_derived=True"):
        RetrievedContextItem(
            item_id="test1", item_type="summary", content="...",
            source_layer=SourceLayer.DRAFT,
            source_artifact="arcs/arc_001/drafts/ch_001.md",
            is_derived=False, trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
        )


def test_runtime_context_no_source():
    item = RetrievedContextItem(
        item_id="test1", item_type="context", content="...",
        is_derived=True, trust_level=RetrievalTrustLevel.RUNTIME_CONTEXT,
    )
    assert item.source_layer is None
    assert item.source_artifact == ""
    assert item.source_artifact_hash is None


def test_runtime_context_with_source_rejected():
    with pytest.raises(ValueError, match="source_layer=None"):
        RetrievedContextItem(
            item_id="test1", item_type="context", content="...",
            source_layer=SourceLayer.DRAFT,
            source_artifact="arcs/arc_001/drafts/ch_001.md",
            is_derived=True, trust_level=RetrievalTrustLevel.RUNTIME_CONTEXT,
        )


def test_runtime_context_with_hash_rejected():
    with pytest.raises(ValueError, match="source_artifact_hash=None"):
        RetrievedContextItem(
            item_id="test1", item_type="context", content="...",
            is_derived=True, trust_level=RetrievalTrustLevel.RUNTIME_CONTEXT,
            source_artifact_hash="abc123",
        )


def test_canonical_must_not_be_derived():
    with pytest.raises(ValueError, match="is_derived=False"):
        RetrievedContextItem(
            item_id="test1", item_type="canon", content="...",
            source_layer=SourceLayer.CANON, source_artifact="canon/approved_outline.md",
            source_artifact_hash="abc123",
            is_derived=True, trust_level=RetrievalTrustLevel.CANONICAL,
        )
