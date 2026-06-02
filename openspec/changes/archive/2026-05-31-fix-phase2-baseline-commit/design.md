## Context

`scripts/verify_phase3_entry_gate.py` treats `Base Commit: unknown` as a
blocking failure. That is correct because the baseline document is meant to be
a single source of truth. The defect is upstream: `tools/verify_test_baseline.py`
defaults `--commit` to `unknown`, making the generated baseline invalid unless
callers remember to provide a commit manually.

## Decision

Resolve the current git commit inside `tools/verify_test_baseline.py` when the
caller omits `--commit`.

The selected behavior is:

- `--commit <value>` keeps using the caller-provided value.
- omitted `--commit` runs `git rev-parse --short HEAD` from the repository root.
- if git resolution fails, the tool exits non-zero instead of writing an
  acceptance-blocking baseline with `unknown`.

## Validation

- Add a focused regression test that patches subprocess execution and verifies
  omitted commit values are resolved from git.
- Re-run the baseline generator against `report.xml`.
- Re-run `scripts/verify_phase3_entry_gate.py`.
- Re-run the full pytest suite.

## Risks

- Running outside a git checkout now fails instead of generating a weak
  baseline. This is intentional because Phase 3 acceptance requires a concrete
  baseline commit.
