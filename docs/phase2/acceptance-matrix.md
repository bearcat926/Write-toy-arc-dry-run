# Phase 3 Acceptance Matrix

**Date:** 2026-05-30

## Phase 3 Entry Gate (13 conditions)

| # | Condition | Verification | Status |
|---|-----------|-------------|--------|
| 1 | All derived artifacts have generation lifecycle | ManifestManager + generation_id in all builders | Implemented |
| 2 | All builder outputs auto-register in Manifest | ManifestManager.register_artifact() called by each builder | Partial (Compressor wired) |
| 3 | stale/missing/hash_mismatch hard fail in active mode | Failure isolation matrix tests | Schema ready |
| 4 | Rollback rebuild by dependency order | RebuildLock + topological rebuild | Lock implemented |
| 5 | Writer/Auditor/Extractor use independent retrieval profiles | RetrievalContextBuilder per-role budgets | Implemented |
| 6 | retrieval_active staged promotion complete | ContextProvider active mode + tests | Implemented |
| 7 | arc_active shadow/dual-run/canary | ArcPlanningEngine + flow integration | Schema ready |
| 8 | 30/50 chapter stress fixtures pass | test_long_arc_context_stress.py (10ch done) | 10ch done, 30/50 pending |
| 9 | Performance hard/trend gate in CI | check_phase2_perf_budget.py | Schema defined |
| 10 | Structured Auditor dual-run + fallback | Phase A/B/C migration | Pending |
| 11 | Drift streak escalation complete | CharacterConsistencyEngine | Engine implemented |
| 12 | Drift gold dataset precision/recall/fpr | Gold dataset + quality framework | Pending |
| 13 | Change Gate upgraded to behavioral Acceptance Matrix | check_phase2_change_gate.py | File-existence checks done |

## Gate Check Commands

```bash
python tools/check_phase2_change_gate.py --target-change milestone0
python tools/check_phase2_change_gate.py --target-change change1
python tools/check_phase2_change_gate.py --target-change change2
python tools/check_phase2_change_gate.py --target-change change3
python tools/check_phase2_change_gate.py --target-change change4
python tools/check_phase2_change_gate.py --target-change change5
```
