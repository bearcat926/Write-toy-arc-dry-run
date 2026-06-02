# Write-toy-arc-dry-run — Project Memory

## Project Identity
- **Name**: novel-workflow (包名), Write-toy-arc-dry-run (仓库)
- **Purpose**: AI 长篇小说创作控制面 — Narrative Operating System
- **Phase**: Phase 3 COMPLETE (2026-06-02)
- **Python**: >=3.11, Pydantic >=2.0, pytest >=7.0

## Phase 3 Completion
- 749 tests passing, 100-chapter stress test passed
- All 10 Phase 3 completion conditions met (Section 24)
- MCP Server (read-only + propose-only), Author Workbench (FastAPI + SPA)
- Audit report: docs/phase3-audit-report.md
- Git: 2 commits on main (5806af9, d1d0926), push to GitHub pending auth

## Architecture
- Kernel: Proposal → Validator → Human Gate → Atomic Apply → Canon + Ledgers
- Agent 禁止直接写 canon/ledgers
- Security: docs/kernel-boundary.md, scripts/scan_forbidden_paths.py

## Key Modules
| Module | File | Purpose |
|--------|------|---------|
| ChapterCommit | schemas/chapter_commit.py | JSONL event log |
| Projections | projection_registry.py | 4 projection types |
| BM25 | bm25_retriever.py | SQLite FTS5 retriever |
| Vector | vector_adapter.py | ABC + TF-IDF fallback |
| Hybrid | hybrid_retriever.py | RRF Fusion + 3 profiles + trace |
| Outbox | outbox_store.py | SQLite lease/retry/DLQ/idempotency |
| Governance | governance_projection.py | shadow/active + hard_pause |
| MCP | mcp_server.py | 5 read-only + 1 propose-only tools |
| API | api.py | FastAPI 7 endpoints |
| Workbench | tools/workbench.html | SPA (Overview/Desk/Health/Trace/Jobs/Rollback) |
| Stress | scripts/run_stress_test.py | N-chapter generator |

## Test Conventions
- Temp directories via tempfile.TemporaryDirectory
- Skip crewai-dependent tests
- Windows symlink tests: pre-existing failures (admin required)
- Direct SQLite queries for time-sensitive tests

## Known Issues
- Windows symlink tests (admin)
- crewai not installed
- sklearn not installed (TF-IDF skipped)
