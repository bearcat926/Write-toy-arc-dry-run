"""Milestone 9: Metrics not retrieval source tests."""
import pytest
from novel_workflow.validators.source_artifact_policy import validate_source_artifact
from novel_workflow.validators.derived_artifact_policy import is_derived_artifact
from novel_workflow.validators.error_codes import SOURCE_ARTIFACT_DENYLISTED


def test_metrics_not_valid_source():
    result = validate_source_artifact("draft", "workspace/metrics.jsonl")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_retrieval_trace_not_valid_source():
    result = validate_source_artifact("draft", "workspace/retrieval_traces/ch_001.jsonl")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_reports_not_valid_source():
    result = validate_source_artifact("draft", "workspace/reports/character_drift_report.md")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_phase2_meta_not_valid_source():
    result = validate_source_artifact("draft", "workspace/phase2/meta.json")
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


def test_metrics_is_derived():
    # metrics is Phase 1, not Phase 2 derived, but still denylisted as source
    # is_derived_artifact checks Phase 2 derived prefixes only
    assert not is_derived_artifact("workspace/metrics.jsonl")


def test_traces_is_derived():
    assert is_derived_artifact("workspace/retrieval_traces/ch_001.jsonl")
