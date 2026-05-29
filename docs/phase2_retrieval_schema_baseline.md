# Phase 2 Retrieval Schema Baseline

**Base commit:** acc99ea
**Status:** Already exists — Phase 2 will extend, not rebuild.

## Current Exports (schemas/retrieval.py)

### Classes
- `RetrievedContextItem(SchemaVersioned)` — single context item with trust level
- `RetrievalRequest(SchemaVersioned)` — request for context building
- `RetrievalTrace(SchemaVersioned, Timestamped)` — audit trail for retrieval

### Functions
- `retrieval_sort_key(item)` — deterministic 5-level sort key

### Constants
- `TRUST_LEVEL_PRIORITY` — trust level → integer priority
- `SOURCE_LAYER_PRIORITY` — source layer → integer priority
- `TRUST_LEVEL_SOURCE_LAYER_MAP` — trust level → expected source layer
- `HASH_REQUIRED_TRUST_LEVELS` — trust levels requiring hash

### Enums (re-exported)
- `RetrievalTrustLevel` — CANONICAL, LEDGER_FACT, WORKING_STATE, DERIVED_SUMMARY, RUNTIME_CONTEXT
- `RetrievalFallbackReason` — 11 fallback reasons
- `ContextBuilderMode` — LEGACY, RETRIEVAL, RETRIEVAL_FALLBACK_LEGACY
- `ProtocolVersion` — PHASE2_V1

## Phase 1 Note
Phase 2 will extend these schemas (add generation_id, trace_write_status, etc.) without breaking existing fields.
