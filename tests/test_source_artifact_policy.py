"""Milestone 2: Source artifact policy tests."""
import pytest
from novel_workflow.validators.source_artifact_policy import validate_source_artifact, is_derived_source
from novel_workflow.validators.error_codes import (
    DERIVED_SOURCE_NOT_ALLOWED,
    INVALID_SOURCE_LAYER,
    SOURCE_ARTIFACT_LAYER_MISMATCH,
    SOURCE_ARTIFACT_DENYLISTED,
)

def test_valid_draft_source():
    result = validate_source_artifact("draft", "arcs/arc_001/drafts/ch_001.md")
    assert result.is_valid


def test_valid_canon_outline():
    result = validate_source_artifact("canon", "canon/approved_outline.md")
    assert result.is_valid


def test_valid_canon_manuscript():
    result = validate_source_artifact("canon", "canon/manuscript/ch_001.md")
    assert result.is_valid


def test_valid_canon_characters():
    result = validate_source_artifact("canon", "canon/characters/character_mind_cards/kael.json")
    assert result.is_valid


def test_valid_arc_working_state():
    result = validate_source_artifact("arc_working_state", "arcs/arc_001/arc_working_state.json")
    assert result.is_valid


def test_workspace_summary_rejected():
    result = validate_source_artifact("draft", "workspace/summaries/ch_001_summary.json")
    assert not result.is_valid
    assert result.error_code == DERIVED_SOURCE_NOT_ALLOWED


def test_workspace_metrics_denylisted():
    result = validate_source_artifact("draft", "workspace/metrics.jsonl")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_workspace_traces_denylisted():
    result = validate_source_artifact("draft", "workspace/retrieval_traces/ch_001.jsonl")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_workspace_reports_denylisted():
    result = validate_source_artifact("draft", "workspace/reports/arc_health_report.md")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_workspace_phase2_denylisted():
    result = validate_source_artifact("draft", "workspace/phase2/meta.json")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_invalid_source_layer():
    # "derived" is not a valid source_layer
    # workspace/summaries check happens first → DERIVED_SOURCE_NOT_ALLOWED
    result = validate_source_artifact("derived", "workspace/summaries/ch_001.json")
    assert not result.is_valid
    assert result.error_code in {SOURCE_ARTIFACT_DENYLISTED, INVALID_SOURCE_LAYER, DERIVED_SOURCE_NOT_ALLOWED}


def test_unknown_source_layer_with_valid_path():
    result = validate_source_artifact("unknown_layer", "arcs/arc_001/drafts/ch_001.md")
    assert not result.is_valid
    assert result.error_code == INVALID_SOURCE_LAYER


def test_layer_path_mismatch():
    result = validate_source_artifact("draft", "canon/approved_outline.md")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_LAYER_MISMATCH


def test_canon_layer_with_draft_path():
    result = validate_source_artifact("canon", "arcs/arc_001/drafts/ch_001.md")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_LAYER_MISMATCH


def test_is_derived_source():
    assert is_derived_source("workspace/summaries/ch_001_summary.json")
    assert is_derived_source("workspace/retrieval_traces/ch_001.jsonl")
    assert is_derived_source("workspace/reports/x.md")
    assert is_derived_source("workspace/phase2/meta.json")
    assert not is_derived_source("arcs/arc_001/drafts/ch_001.md")
    assert not is_derived_source("canon/approved_outline.md")
