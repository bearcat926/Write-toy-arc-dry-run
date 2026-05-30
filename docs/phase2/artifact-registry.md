# Phase 2.1 Artifact Registry

**Date:** 2026-05-30
**Base:** main (364cc5b)

## Artifact Type Registry

| # | ArtifactType | Owner Change | Builder | Consumer | Path Pattern | Retention |
|---|---|---|---|---|---|---|
| 1 | NARRATIVE_SUMMARY | change2 | NarrativeCompressor | RetrievalContextBuilder, GraphBuilder | workspace/summaries/ch_*_summary.json | keep_all |
| 2 | ARC_SUMMARY | change2 | NarrativeCompressor | RetrievalContextBuilder | workspace/summaries/arc_*_summary.json | keep_all |
| 3 | RETRIEVAL_TRACE | change1 | ContextProvider | Audit | workspace/retrieval_traces/ch_*.jsonl | 14d |
| 4 | PHASE2_META | change1 | Manual | Audit | workspace/phase2/meta.json | keep_all |
| 5 | NARRATIVE_GRAPH_INDEX | change3 | NarrativeGraphBuilder | LifecycleMgr, DriftEngine | workspace/narrative_graph_index.json | 3 generations |
| 6 | FORESHADOW_LIFECYCLE_INDEX | change3 | ForeshadowLifecycleMgr | DriftEngine, ArcPlanner | workspace/foreshadow_lifecycle_index.json | 3 generations |
| 7 | GRAPH_HEALTH_REPORT | change3 | GraphBuilder | Audit | workspace/reports/graph_health_report.* | 30d |
| 8 | FORESHADOW_LIFECYCLE_REPORT | change3 | LifecycleMgr | Audit | workspace/reports/foreshadow_lifecycle_report.* | 30d |
| 9 | CHARACTER_STATE_SNAPSHOT | change4 | ConsistencyEngine | DriftEngine | workspace/character_state/*.json | 3 generations |
| 10 | CHARACTER_DRIFT_REPORT | change4 | ConsistencyEngine | Audit, ArcPlanner | workspace/reports/character_drift_report_* | 30d |
| 11 | DRIFT_HEALTH_REPORT | change4 | ConsistencyEngine | Audit | workspace/reports/drift_health_report.* | 30d |
| 12 | STRUCTURED_AUDIT_REPORT | change4 | Auditor | Engine | workspace/reports/structured_audit_report.* | 30d |
| 13 | ARC_PLAN | change5 | ArcPlanningEngine | Flow | workspace/arc_plan/arc_*_plan.json | keep_all |
| 14 | CHAPTER_BEAT_PLAN | change5 | ArcPlanningEngine | Flow, Auditor | workspace/arc_plan/arc_*_ch_*_beat_plan.json | 3 generations |
| 15 | ARC_HEALTH_REPORT | change5 | ArcPlanningEngine | Audit | workspace/reports/arc_health_report_* | 30d |
| 16 | ARC_PLANNING_TRACE | change5 | ArcPlanningEngine | Audit | workspace/retrieval_traces/arc_*_planning.jsonl | 14d |

## Cross-cutting

| Artifact | Owner | Builder | Path |
|---|---|---|---|
| manifest.json | global | ManifestManager | workspace/phase2/manifest.json |
| rebuild.lock | global | RebuildLock | workspace/phase2/rebuild.lock |

## Rules

- All artifacts: `derived=true`, `source_of_truth=false`
- Forbidden consumers: ProposalValidator, LedgerApplyEngine, CanonWriter
- Active mode: only `stale=false` + `source_hash_validation_status=valid`
