"""Milestone 0: Protocol enum tests."""
import pytest
from novel_workflow.schemas.enums import (
    SourceLayer, ArtifactType, ProtocolVersion,
    RetrievalTrustLevel, RetrievalFallbackReason,
    ContextBuilderMode, HashStrategy,
)


def test_source_layer_values():
    assert SourceLayer.DRAFT.value == "draft"
    assert SourceLayer.CANON.value == "canon"
    assert SourceLayer.ARC_WORKING_STATE.value == "arc_working_state"


def test_source_layer_invalid():
    with pytest.raises(ValueError):
        SourceLayer("DRAFT")
    with pytest.raises(ValueError):
        SourceLayer("draft ")
    with pytest.raises(ValueError):
        SourceLayer("canon_v2")


def test_artifact_type_phase2_values():
    assert ArtifactType.NARRATIVE_SUMMARY.value == "narrative_summary"
    assert ArtifactType.ARC_SUMMARY.value == "arc_summary"
    assert ArtifactType.RETRIEVAL_TRACE.value == "retrieval_trace"
    assert ArtifactType.PHASE2_META.value == "phase2_meta"


def test_artifact_type_phase1_preserved():
    assert ArtifactType.CONSUMED_HASHES.value == "consumed_hashes"
    assert ArtifactType.PROGRESS.value == "progress"
    assert ArtifactType.GATE_RECORD.value == "gate_record"


def test_artifact_type_invalid():
    with pytest.raises(ValueError):
        ArtifactType("truly_nonexistent_type_xyz")  # not in enum


def test_artifact_type_phase2_future_values():
    """Verify all Phase 2 future artifact types are registered."""
    assert ArtifactType.NARRATIVE_GRAPH_INDEX.value == "narrative_graph_index"
    assert ArtifactType.FORESHADOW_LIFECYCLE_INDEX.value == "foreshadow_lifecycle_index"
    assert ArtifactType.GRAPH_HEALTH_REPORT.value == "graph_health_report"
    assert ArtifactType.FORESHADOW_LIFECYCLE_REPORT.value == "foreshadow_lifecycle_report"
    assert ArtifactType.CHARACTER_STATE_SNAPSHOT.value == "character_state_snapshot"
    assert ArtifactType.CHARACTER_DRIFT_REPORT.value == "character_drift_report"
    assert ArtifactType.DRIFT_HEALTH_REPORT.value == "drift_health_report"
    assert ArtifactType.STRUCTURED_AUDIT_REPORT.value == "structured_audit_report"
    assert ArtifactType.ARC_PLAN.value == "arc_plan"
    assert ArtifactType.CHAPTER_BEAT_PLAN.value == "chapter_beat_plan"
    assert ArtifactType.ARC_HEALTH_REPORT.value == "arc_health_report"
    assert ArtifactType.ARC_PLANNING_TRACE.value == "arc_planning_trace"


def test_protocol_version():
    assert ProtocolVersion.PHASE2_V1.value == "phase2_v1"
    with pytest.raises(ValueError):
        ProtocolVersion("phase2_v2")


def test_retrieval_trust_level():
    assert RetrievalTrustLevel.CANONICAL.value == "canonical"
    assert RetrievalTrustLevel.RUNTIME_CONTEXT.value == "runtime_context"


def test_retrieval_fallback_reason():
    assert RetrievalFallbackReason.SUMMARY_STALE.value == "SUMMARY_STALE"
    assert RetrievalFallbackReason.CONTEXT_BUDGET_EXCEEDED.value == "CONTEXT_BUDGET_EXCEEDED"


def test_context_builder_mode():
    assert ContextBuilderMode.LEGACY.value == "legacy"
    assert ContextBuilderMode.RETRIEVAL.value == "retrieval"
    assert ContextBuilderMode.RETRIEVAL_FALLBACK_LEGACY.value == "retrieval_fallback_legacy"


def test_hash_strategy():
    assert HashStrategy.TEXT_CANONICAL.value == "text_canonical"
    assert HashStrategy.JSON_CANONICAL.value == "json_canonical"
    assert HashStrategy.NOT_HASHED.value == "not_hashed"


def test_enum_string_comparison():
    assert SourceLayer.DRAFT == "draft"
    assert ArtifactType.NARRATIVE_SUMMARY == "narrative_summary"
