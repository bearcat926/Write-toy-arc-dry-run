# Phase 2.1 Runtime DAG

**Date:** 2026-05-30

## Module Dependency Graph

```
canon / ledgers / approved_outline
        ↓
    chapter draft
        ↓
  ┌─────────────────────┐
  │ NarrativeCompressor  │ ← summary schema
  └─────────┬───────────┘
            ↓
    chapter_summary (derived)
            ↓
  ┌─────────────────────┐
  │ RetrievalContextBuilder │ ← retrieval schema
  └─────────┬───────────┘
            ↓
    context_string + RetrievalTrace (derived)
            ↓
  ┌─────────────────────┐
  │ ContextProvider      │ ← flow.py
  └─────────┬───────────┘
            ↓
    Writer / Auditor / Extractor prompt
            ↓
  ┌─────────────────────┐
  │ NarrativeGraphBuilder │ (Wave 3)
  └─────────┬───────────┘
            ↓
    narrative_graph_index (derived)
            ↓
  ┌───────────────────────┐
  │ ForeshadowLifecycleMgr │ (Wave 3)
  └─────────┬─────────────┘
            ↓
    foreshadow_lifecycle_index (derived)
            ↓
  ┌─────────────────────────┐
  │ CharacterConsistencyEngine│ (Wave 3)
  └─────────┬───────────────┘
            ↓
    character_drift_report (derived)
            ↓
  ┌─────────────────────────┐
  │ ArcPlanningEngine        │ (Wave 4)
  └─────────┬───────────────┘
            ↓
    arc_plan + chapter_beat_plan (derived)
            ↓
  ┌─────────────────────────┐
  │ ManifestManager          │
  └──────────────────────────┘
```

## Cross-cutting

- **ManifestManager**: 所有 builder 产出都登记 manifest
- **RebuildLock**: 并发 rebuild 保护
- **ChangeGate**: CI 门控

## Stale Propagation

```
draft changed
  → summary stale
    → graph stale
      → lifecycle stale
        → drift stale
          → arc_plan stale
```

Rollback 触发全链路 stale + rebuild。
