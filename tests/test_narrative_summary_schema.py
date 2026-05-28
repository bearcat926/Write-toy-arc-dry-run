"""Milestone 5: Narrative summary schema tests."""
import pytest
from pydantic import ValidationError
from novel_workflow.schemas.narrative_summary import ChapterNarrativeSummary
from novel_workflow.schemas.enums import SourceLayer, ProtocolVersion


def test_valid_summary():
    s = ChapterNarrativeSummary(
        chapter_id="ch_001", arc_id="arc_001",
        source_layer=SourceLayer.DRAFT,
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        source_artifact_hash="abc123",
    )
    assert s.derived is True
    assert s.protocol_version == ProtocolVersion.PHASE2_V1


def test_summary_must_be_derived():
    with pytest.raises(ValidationError, match="SUMMARY_NOT_DERIVED"):
        ChapterNarrativeSummary(
            chapter_id="ch_001", arc_id="arc_001",
            source_layer=SourceLayer.DRAFT,
            source_artifact="arcs/arc_001/drafts/ch_001.md",
            source_artifact_hash="abc123",
            derived=False,
        )


def test_summary_source_must_be_draft():
    with pytest.raises(ValidationError, match="SUMMARY_SOURCE_LAYER_INVALID"):
        ChapterNarrativeSummary(
            chapter_id="ch_001", arc_id="arc_001",
            source_layer=SourceLayer.CANON,
            source_artifact="canon/approved_outline.md",
            source_artifact_hash="abc123",
        )


def test_summary_source_not_workspace():
    with pytest.raises(ValidationError, match="SUMMARY_SOURCE_NOT_ALLOWED"):
        ChapterNarrativeSummary(
            chapter_id="ch_001", arc_id="arc_001",
            source_layer=SourceLayer.DRAFT,
            source_artifact="workspace/summaries/ch_001_summary.json",
            source_artifact_hash="abc123",
        )


def test_summary_with_arc_working_state_rejected():
    with pytest.raises(ValidationError, match="SUMMARY_SOURCE_LAYER_INVALID"):
        ChapterNarrativeSummary(
            chapter_id="ch_001", arc_id="arc_001",
            source_layer=SourceLayer.ARC_WORKING_STATE,
            source_artifact="arcs/arc_001/arc_working_state.json",
            source_artifact_hash="abc123",
        )


def test_summary_serialization():
    s = ChapterNarrativeSummary(
        chapter_id="ch_001", arc_id="arc_001",
        source_layer=SourceLayer.DRAFT,
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        source_artifact_hash="abc123",
    )
    data = s.model_dump(mode="json")
    assert data["derived"] is True
    assert data["source_layer"] == "draft"
    assert data["schema_version"] == "1.0"
