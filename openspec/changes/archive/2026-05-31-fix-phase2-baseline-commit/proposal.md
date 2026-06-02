## Why

Phase 3 entry verification fails when `docs/phase2_test_baseline.generated.md`
records `Base Commit: unknown`. The baseline generator currently allows that
invalid value by default, so the verification chain can generate a fact source
that later blocks acceptance.

## What Changes

- Make `tools/verify_test_baseline.py` resolve the current git commit when
  `--commit` is not provided.
- Preserve the explicit `--commit` override for reproducible external runs.
- Add regression coverage for the default commit resolution behavior.
- Regenerate the Phase 2 baseline document with a concrete commit.

## Capabilities

### New Capabilities

- `phase3-entry-gate-verification`: Baseline generation and Phase 3 entry gate
  verification must share the same machine-verifiable commit requirement.

### Modified Capabilities

- None.

## Impact

- Affected files: `tools/verify_test_baseline.py`,
  `tests/test_verify_test_baseline.py`, and
  `docs/phase2_test_baseline.generated.md`.
- No public API, dependency, schema, or runtime architecture changes.
