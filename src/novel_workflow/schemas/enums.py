"""Phase 2 protocol enums — centralized for consistency."""
from enum import Enum


class SourceLayer(str, Enum):
    DRAFT = "draft"
    CANON = "canon"
    ARC_WORKING_STATE = "arc_working_state"


class ArtifactType(str, Enum):
    # Phase 1 existing
    DRAFT = "draft"
    REVIEW = "review"
    PROPOSAL = "proposal"
    GATE_RECORD = "gate_record"
    APPLY_RECORD = "apply_record"
    ROLLBACK_SNAPSHOT = "rollback_snapshot"
    CONSUMED_HASHES = "consumed_hashes"
    PROGRESS = "progress"
    METRICS = "metrics"
    DASHBOARD = "dashboard"
    ARC_WORKING_STATE = "arc_working_state"
    LEDGER_DIFF = "ledger_diff"
    CANON_DIFF = "canon_diff"
    CHECKPOINT = "checkpoint"
    PAUSE_REPORT = "pause_report"
    ARC_REPORT = "arc_report"
    CANON_MANUSCRIPT = "canon_manuscript"
    CANON_CHARACTERS = "canon_characters"
    CANON_MANUSCRIPT_COPY = "canon_manuscript_copy"
    CANON_CHARACTER_UPDATE = "canon_character_update"
    LEDGERS = "ledgers"
    ARC_CONTRACT = "arc_contract"
    DIRECTION_GATE = "direction_gate"
    INVERSE_DIFF = "inverse_diff"
    # Phase 2 new
    NARRATIVE_SUMMARY = "narrative_summary"
    ARC_SUMMARY = "arc_summary"
    RETRIEVAL_TRACE = "retrieval_trace"
    PHASE2_META = "phase2_meta"
    # Phase 2 future (Milestone 2-5)
    NARRATIVE_GRAPH_INDEX = "narrative_graph_index"
    FORESHADOW_LIFECYCLE_INDEX = "foreshadow_lifecycle_index"
    GRAPH_HEALTH_REPORT = "graph_health_report"
    FORESHADOW_LIFECYCLE_REPORT = "foreshadow_lifecycle_report"
    CHARACTER_STATE_SNAPSHOT = "character_state_snapshot"
    CHARACTER_DRIFT_REPORT = "character_drift_report"
    DRIFT_HEALTH_REPORT = "drift_health_report"
    STRUCTURED_AUDIT_REPORT = "structured_audit_report"
    ARC_PLAN = "arc_plan"
    CHAPTER_BEAT_PLAN = "chapter_beat_plan"
    ARC_HEALTH_REPORT = "arc_health_report"
    ARC_PLANNING_TRACE = "arc_planning_trace"


class ProtocolVersion(str, Enum):
    PHASE2_V1 = "phase2_v1"


class RetrievalTrustLevel(str, Enum):
    CANONICAL = "canonical"
    LEDGER_FACT = "ledger_fact"
    WORKING_STATE = "working_state"
    DERIVED_SUMMARY = "derived_summary"
    RUNTIME_CONTEXT = "runtime_context"


class RetrievalFallbackReason(str, Enum):
    SUMMARY_MISSING = "SUMMARY_MISSING"
    SUMMARY_STALE = "SUMMARY_STALE"
    SUMMARY_SCHEMA_UNSUPPORTED = "SUMMARY_SCHEMA_UNSUPPORTED"
    SUMMARY_NOT_DERIVED = "SUMMARY_NOT_DERIVED"
    SUMMARY_SOURCE_MISSING = "SUMMARY_SOURCE_MISSING"
    SUMMARY_SOURCE_PATH_MISMATCH = "SUMMARY_SOURCE_PATH_MISMATCH"
    SUMMARY_MULTIPLE_CANDIDATES = "SUMMARY_MULTIPLE_CANDIDATES"
    RETRIEVAL_TIMEOUT = "RETRIEVAL_TIMEOUT"
    TRACE_WRITE_FAILED = "TRACE_WRITE_FAILED"
    CONTEXT_BUDGET_EXCEEDED = "CONTEXT_BUDGET_EXCEEDED"
    RETRIEVAL_EXCEPTION = "RETRIEVAL_EXCEPTION"


class ContextBuilderMode(str, Enum):
    LEGACY = "legacy"
    RETRIEVAL = "retrieval"
    RETRIEVAL_FALLBACK_LEGACY = "retrieval_fallback_legacy"


class HashStrategy(str, Enum):
    TEXT_CANONICAL = "text_canonical"
    JSON_CANONICAL = "json_canonical"
    RAW_SHA256 = "raw_sha256"
    NOT_HASHED = "not_hashed"
