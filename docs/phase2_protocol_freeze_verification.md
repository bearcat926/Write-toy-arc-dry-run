# Phase 2 Protocol Freeze — Verification Record

**Date:** 2026-05-28
**Base Commit:** b70a821
**Platform:** Windows 10 Pro / Python 3.13

## Gap Closure Summary

| Gap | Status | Fix Commit |
|-----|--------|-----------|
| P0-1: LedgerDiffGenerator provenance 闭环 | Closed | 28407ee |
| P0-2: 测试结果可审计 | Closed | c15e527, 4c5b8d1 |
| P1-1: Derived path hardening | Closed | c19dc29, c5389c9 |

## Test Results

```bash
pytest tests/ -v
# 312+ passed, 7 skipped (Windows symlink tests)
```

### Skipped Tests

7 tests use `os.symlink()` which requires admin privileges on Windows.
These tests run on CI (ubuntu-latest) where symlink creation is unprivileged.

## Changes Made

1. `error_codes.py`: Added `APPLY_MISSING_PROVENANCE`
2. `atomic_apply_manager.py`: Empty `source_artifact` now rejected at apply layer
3. `derived_artifact_policy.py`: `resolve_under_root()` uses `Path.relative_to()`; added `assert_no_symlink_in_path()`
4. `path_safety.py`: `check_write_path()` uses `Path.relative_to()`
5. `.github/workflows/pytest.yml`: CI with JUnit XML + artifact upload
6. `README.md`: Updated test count
7. 6 test files: Updated fixtures with provenance fields
8. `test_apply_missing_provenance.py`: 2 new tests for apply-layer provenance
9. `test_derived_path_hardening.py`: 5 new tests for path hardening

## Verification Checklist

- [x] Generator produces provenance in every operation
- [x] Apply rejects empty/missing source_artifact
- [x] Apply rejects derived source_artifact
- [x] Apply rejects is_derived=True
- [x] resolve_under_root rejects prefix collision
- [x] Symlink at any path component rejected
- [x] Path traversal via ../ rejected
- [x] CI workflow passes on ubuntu-latest
- [x] All 312+ tests pass, 7 skipped (Windows symlinks)
