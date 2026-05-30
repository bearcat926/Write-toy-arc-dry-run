"""Retrieval schemas — context selection artifacts for Phase 2."""
from typing import Literal
from pydantic import field_validator
from .common import SchemaVersioned, Timestamped
from .enums import (
    SourceLayer,
    RetrievalTrustLevel,
    RetrievalFallbackReason,
    ContextBuilderMode,
    ProtocolVersion,
)

# Deterministic priority by trust level
TRUST_LEVEL_PRIORITY: dict[RetrievalTrustLevel, int] = {
    RetrievalTrustLevel.CANONICAL: 100,
    RetrievalTrustLevel.LEDGER_FACT: 90,
    RetrievalTrustLevel.WORKING_STATE: 80,
    RetrievalTrustLevel.DERIVED_SUMMARY: 55,
    RetrievalTrustLevel.DERIVED_GRAPH: 50,
    RetrievalTrustLevel.DERIVED_LIFECYCLE: 45,
    RetrievalTrustLevel.DERIVED_DRIFT: 35,
    RetrievalTrustLevel.DERIVED_ARC_PLAN: 30,
    RetrievalTrustLevel.RUNTIME_CONTEXT: 10,
}

# Deterministic priority by source layer
SOURCE_LAYER_PRIORITY: dict[SourceLayer | None, int] = {
    SourceLayer.CANON: 100,
    SourceLayer.ARC_WORKING_STATE: 80,
    SourceLayer.DRAFT: 60,
    None: 0,
}

# Trust level → allowed source_layer mapping
TRUST_LEVEL_SOURCE_LAYER_MAP: dict[RetrievalTrustLevel, SourceLayer | None] = {
    RetrievalTrustLevel.CANONICAL: SourceLayer.CANON,
    RetrievalTrustLevel.LEDGER_FACT: SourceLayer.CANON,
    RetrievalTrustLevel.WORKING_STATE: SourceLayer.ARC_WORKING_STATE,
    RetrievalTrustLevel.DERIVED_SUMMARY: SourceLayer.DRAFT,
    RetrievalTrustLevel.DERIVED_GRAPH: None,
    RetrievalTrustLevel.DERIVED_LIFECYCLE: None,
    RetrievalTrustLevel.DERIVED_DRIFT: None,
    RetrievalTrustLevel.DERIVED_ARC_PLAN: None,
    RetrievalTrustLevel.RUNTIME_CONTEXT: None,
}

# Trust levels that require source_artifact_hash
HASH_REQUIRED_TRUST_LEVELS = {
    RetrievalTrustLevel.CANONICAL,
    RetrievalTrustLevel.LEDGER_FACT,
    RetrievalTrustLevel.WORKING_STATE,
}


class RetrievedContextItem(SchemaVersioned):
    item_id: str
    item_type: str
    content: str
    source_layer: SourceLayer | None = None
    source_artifact: str = ""
    source_artifact_hash: str | None = None
    is_derived: bool = False
    trust_level: RetrievalTrustLevel
    relevance_reason: str = ""
    priority: int = 0
    selection_reason: str = ""
    source_hash_validation_status: Literal["valid", "stale", "missing", "not_required"] = "not_required"

    @field_validator("trust_level")
    @classmethod
    def validate_trust_source_consistency(cls, v: RetrievalTrustLevel, info) -> RetrievalTrustLevel:
        source_layer = info.data.get("source_layer")
        is_derived = info.data.get("is_derived", False)
        source_artifact_hash = info.data.get("source_artifact_hash")

        expected_layer = TRUST_LEVEL_SOURCE_LAYER_MAP.get(v)

        # runtime_context must have None source_layer
        if v == RetrievalTrustLevel.RUNTIME_CONTEXT:
            if source_layer is not None:
                raise ValueError("runtime_context must have source_layer=None")
            source_artifact = info.data.get("source_artifact", "")
            if source_artifact:
                raise ValueError("runtime_context must have empty source_artifact")
            if source_artifact_hash is not None:
                raise ValueError("runtime_context must have source_artifact_hash=None")
        else:
            # Non-runtime must match expected source_layer
            if expected_layer is not None and source_layer != expected_layer:
                raise ValueError(
                    f"trust_level={v.value} requires source_layer={expected_layer.value}"
                )

        # canonical/ledger_fact/working_state require hash
        if v in HASH_REQUIRED_TRUST_LEVELS:
            if not source_artifact_hash:
                raise ValueError(f"trust_level={v.value} requires source_artifact_hash")

        # All DERIVED_* must have is_derived=True
        if v.value.startswith("derived_"):
            if not is_derived:
                raise ValueError(f"trust_level={v.value} must have is_derived=True")

        # canonical/ledger_fact/working_state must NOT be derived
        if v in {RetrievalTrustLevel.CANONICAL, RetrievalTrustLevel.LEDGER_FACT,
                  RetrievalTrustLevel.WORKING_STATE}:
            if is_derived:
                raise ValueError(f"trust_level={v.value} must have is_derived=False")

        return v

    @field_validator("source_hash_validation_status")
    @classmethod
    def validate_hash_status(cls, v: str, info) -> str:
        trust_level = info.data.get("trust_level")
        if trust_level and trust_level in HASH_REQUIRED_TRUST_LEVELS:
            if v != "valid":
                raise ValueError(f"trust_level={trust_level.value} requires source_hash_validation_status='valid'")
        if trust_level == RetrievalTrustLevel.RUNTIME_CONTEXT:
            if v != "not_required":
                raise ValueError("runtime_context requires source_hash_validation_status='not_required'")
        return v


class RetrievalRequest(SchemaVersioned):
    arc_id: str
    chapter_id: str
    agent_role: Literal["writer", "auditor", "extractor"]
    max_character_budget: int = 12000


class RetrievalTrace(SchemaVersioned, Timestamped):
    request: RetrievalRequest
    selected_items: list[RetrievedContextItem] = []
    dropped_items: list[dict] = []
    final_character_count: int = 0
    estimated_token_count: int = 0
    fallback_used: bool = False
    fallback_reason: RetrievalFallbackReason | None = None
    context_builder_mode: ContextBuilderMode = ContextBuilderMode.LEGACY
    chapter_id: str = ""
    agent_role: str = ""
    attempt_id: str = ""
    derived: bool = True
    generation_id: str = ""
    context_mode: ContextBuilderMode = ContextBuilderMode.LEGACY
    trace_write_error: str | None = None
    trace_write_status: Literal["written", "failed"] = "written"
    ranking_features: dict = {}

    @field_validator("trace_write_status")
    @classmethod
    def validate_trace_write(cls, v: str, info) -> str:
        error = info.data.get("trace_write_error")
        if v == "failed" and not error:
            raise ValueError("trace_write_status='failed' requires trace_write_error")
        return v


def retrieval_sort_key(item: RetrievedContextItem) -> tuple:
    """Deterministic sort key for retrieval items (5-level)."""
    def canonicalize_path_for_sort(path: str) -> str:
        """Normalize path for sorting only — NOT for security."""
        return path.replace("\\", "/").strip().lower()

    return (
        -TRUST_LEVEL_PRIORITY.get(item.trust_level, 0),
        -SOURCE_LAYER_PRIORITY.get(item.source_layer, 0),
        -item.priority,
        canonicalize_path_for_sort(item.source_artifact),
        item.item_id,
    )
