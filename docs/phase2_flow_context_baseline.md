# Phase 2 Flow Context Baseline

**Base commit:** acc99ea

## Current Context Path

### `_build_context(root, arc_id, current_ch)` (flow.py:54-83)

Builds context string by concatenating:

1. **Arc Working State** — `arcs/<arc_id>/arc_working_state.json` (full content)
2. **Approved Outline** — `canon/approved_outline.md` (full content)
3. **All Ledgers** — `ledgers/*.json` (full content, glob all)
4. **Previous Chapters** — `arcs/<arc_id>/drafts/ch_XXX.md` (first 500 chars each)

Returns: joined string with `## Section Title` headers, or `"(empty project)"`.

### Main Chapter Loop

`_build_context()` is called to build Writer context. The same context is passed to Auditor and Extractor roles.

### Revision Loop

`_run_revision_loop()` also calls `_build_context()` for rewrite/re-audit/re-extract cycles.

## Phase 2 Impact

Change 1 will introduce `ContextProvider` to replace direct `_build_context()` calls.
Both main loop and revision loop must go through `ContextProvider`.
`_build_context()` will be preserved as legacy fallback implementation.
