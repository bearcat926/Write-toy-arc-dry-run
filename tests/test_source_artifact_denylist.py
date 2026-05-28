"""Milestone 2.6: Source artifact denylist tests."""
import pytest
from novel_workflow.validators.source_artifact_policy import validate_source_artifact
from novel_workflow.validators.error_codes import SOURCE_ARTIFACT_DENYLISTED, DERIVED_SOURCE_NOT_ALLOWED


DENYLISTED_PATHS = [
    "workspace/metrics.jsonl",
    "workspace/retrieval_traces/ch_001.jsonl",
    "workspace/retrieval_traces/ch_999.jsonl",
    "workspace/reports/arc_health_report.md",
    "workspace/reports/character_drift_report.md",
    "workspace/reports/foreshadow_lifecycle_report.md",
    "workspace/phase2/meta.json",
]

DERIVED_SUMMARY_PATHS = [
    "workspace/summaries/ch_001_summary.json",
    "workspace/summaries/arc_001_summary.json",
]


@pytest.mark.parametrize("path", DENYLISTED_PATHS)
def test_denylisted_paths(path):
    result = validate_source_artifact("draft", path)
    assert not result.is_valid
    assert result.error_code == SOURCE_ARTIFACT_DENYLISTED


@pytest.mark.parametrize("path", DERIVED_SUMMARY_PATHS)
def test_derived_summary_paths(path):
    result = validate_source_artifact("draft", path)
    assert not result.is_valid
    assert result.error_code == DERIVED_SOURCE_NOT_ALLOWED
