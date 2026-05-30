# Phase 2.1 Promotion Policy

**Date:** 2026-05-30

## Mode Promotion Ladder

```
legacy → shadow → retrieval_active → arc_active
```

## Promotion Rules

### legacy → shadow
- No code changes required (env var: `NOVEL_WORKFLOW_CONTEXT_MODE=retrieval_shadow`)
- Shadow generates trace but does NOT change prompt
- Minimum: 3 CI runs, no manifest failures

### shadow → retrieval_active
- **Prerequisites:**
  - ManifestManager wired to all builders
  - RebuildLock tested
  - Failure isolation matrix tests pass
  - stale/missing/hash_mismatch hard fail tests pass
  - retrieval trace generation_id present
  - source_hash_validation_status present
- **Minimum observation:** 3 CI runs in shadow mode, no staleness
- **Gate:** `check_phase2_change_gate.py --target-change change2` PASS

### retrieval_active → arc_active
- **Prerequisites:**
  - ArcPlan/ChapterBeatPlan schema validated
  - ArcPlanningEngine generates plans from arc_contract
  - Writer beat injection tested
  - Auditor beat alignment tested
  - 30 chapter stress pass
  - Performance hard gate pass
- **Minimum observation:** 3 CI runs in retrieval_active, no context explosion
- **Gate:** `check_phase2_change_gate.py --target-change change5` PASS

## Forbidden Transitions
- shadow → arc_active (must go through retrieval_active)
- Any mode + best_effort in active modes
- Any mode that skips Change gate

## Rollback
- Any mode can roll back to previous mode immediately
- Rollback triggers manifest stale marking
- Rollback triggers rebuild of affected derived artifacts
