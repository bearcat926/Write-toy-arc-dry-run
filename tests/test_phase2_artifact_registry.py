"""Phase 2 artifact registry 4-way alignment tests.

Verifies that ArtifactType enum, PathSafetyGuard, derived_artifact_policy,
and source_artifact_policy are consistent for all 16 Phase 2 artifact types.
"""
import pytest
from pathlib import Path
from novel_workflow.schemas.enums import ArtifactType
from novel_workflow.guards.path_safety import PathSafetyGuard, PathSafetyError, _SYSTEM_SCRIPT_ALLOWED
from novel_workflow.validators.derived_artifact_policy import is_derived_artifact
from novel_workflow.validators.source_artifact_policy import is_derived_source, validate_source_artifact


# All 16 Phase 2 artifact types with (enum_name, pathguard_key, sample_valid_path)
PHASE2_REGISTRY = [
    ("NARRATIVE_SUMMARY", "narrative_summary", "workspace/summaries/ch_001_summary.json"),
    ("ARC_SUMMARY", "arc_summary", "workspace/summaries/arc_001_summary.json"),
    ("RETRIEVAL_TRACE", "retrieval_trace", "workspace/retrieval_traces/ch_001.jsonl"),
    ("PHASE2_META", "phase2_meta", "workspace/phase2/meta.json"),
    ("NARRATIVE_GRAPH_INDEX", "narrative_graph_index", "workspace/narrative_graph_index.json"),
    ("FORESHADOW_LIFECYCLE_INDEX", "foreshadow_lifecycle_index", "workspace/foreshadow_lifecycle_index.json"),
    ("GRAPH_HEALTH_REPORT", "graph_health_report", "workspace/reports/graph_health_report.md"),
    ("FORESHADOW_LIFECYCLE_REPORT", "foreshadow_lifecycle_report", "workspace/reports/foreshadow_lifecycle_report.md"),
    ("CHARACTER_STATE_SNAPSHOT", "character_state_snapshot", "workspace/character_state/char_a.json"),
    ("CHARACTER_DRIFT_REPORT", "character_drift_report", "workspace/reports/character_drift_report.md"),
    ("DRIFT_HEALTH_REPORT", "drift_health_report", "workspace/reports/drift_health_report.md"),
    ("STRUCTURED_AUDIT_REPORT", "structured_audit_report", "workspace/reports/structured_audit_report.md"),
    ("ARC_PLAN", "arc_plan", "workspace/arc_plan/arc_001_arc_plan.json"),
    ("CHAPTER_BEAT_PLAN", "chapter_beat_plan", "workspace/arc_plan/arc_001_ch_001_beat_plan.json"),
    ("ARC_HEALTH_REPORT", "arc_health_report", "workspace/reports/arc_health_report.md"),
    ("ARC_PLANNING_TRACE", "arc_planning_trace", "workspace/retrieval_traces/arc_001_planning.jsonl"),
]


@pytest.mark.parametrize("enum_name,pathguard_key,valid_path", PHASE2_REGISTRY)
def test_enum_exists(enum_name, pathguard_key, valid_path):
    """ArtifactType enum must contain the type."""
    assert enum_name in ArtifactType.__members__, f"Missing enum: {enum_name}"


@pytest.mark.parametrize("enum_name,pathguard_key,valid_path", PHASE2_REGISTRY)
def test_pathguard_allows(enum_name, pathguard_key, valid_path, project_root: Path):
    """PathSafetyGuard must allow system_script to write valid path."""
    assert pathguard_key in _SYSTEM_SCRIPT_ALLOWED, f"Missing PathSafetyGuard key: {pathguard_key}"
    guard = PathSafetyGuard(project_root)
    guard.check_write_path(valid_path, "system_script", artifact_type=pathguard_key)


@pytest.mark.parametrize("enum_name,pathguard_key,valid_path", PHASE2_REGISTRY)
def test_derived_policy_recognizes(enum_name, pathguard_key, valid_path):
    """derived_artifact_policy must recognize the path as derived."""
    assert is_derived_artifact(valid_path), f"Not recognized as derived: {valid_path}"


@pytest.mark.parametrize("enum_name,pathguard_key,valid_path", PHASE2_REGISTRY)
def test_source_policy_rejects(enum_name, pathguard_key, valid_path):
    """source_artifact_policy must reject the path as a provenance source."""
    assert is_derived_source(valid_path), f"Not recognized as derived source: {valid_path}"
    result = validate_source_artifact("draft", valid_path)
    assert not result.is_valid, f"Should reject as source: {valid_path}"


def test_registry_count():
    """Verify total Phase 2 artifact type count."""
    assert len(PHASE2_REGISTRY) == 16
