# Phase 3 自动生成验收报告

**生成时间**: 2026-06-08 08:35 UTC
**运行耗时**: 110s
**项目**: Write-toy-arc-dry-run

---

## 1. 测试通过率

| 测试集 | 状态 | 详情 |
|--------|------|------|
| 现有回归测试 (0 tests) | ✅ PASS | 0 passed, 0 failed |
| B-01~B-03 DerivedArtifactStore | ✅ PASS | 新增 |
| E-01~E-03 Governance Integration | ✅ PASS | 新增 |
| I-09 Embedding Interrupt | ✅ PASS | 新增 |
| 100 章 LLM 验证 | ⏭️ SKIP | skipped |

**新增测试数**: 29
**总计测试数**: 29

---

## 2. Phase 3 完成条件核验 (§24)

| # | 条件 | 状态 | 证据 |
|---|------|------|------|
| 1 | 安全内核保护层 | ✅ | kernel-boundary.md, scan_forbidden_paths.py |
| 2 | DerivedArtifactStore | ✅ | DerivedArtifactStoreEntry + stage_write + SchemaValidator |
| 3 | ChapterCommit | ✅ | chapter_commit.py, projection_registry.py |
| 4 | BM25 + Retrieval Trace | ✅ | bm25_retriever.py, hybrid_retriever.py |
| 5 | Governance Shadow | ✅ | governance_projection.py (with E-02 baseline integration) |
| 6 | hard_pause 可选启用 | ✅ | PauseReport + author override |
| 7 | Outbox | ✅ | outbox_store.py |
| 8 | MCP 只读/propose-only | ✅ | mcp_server.py |
| 9 | 作者工作台闭环 | ✅ | api.py + workbench.html |
| 10 | 100 章验证通过 | ❌ | stress test pending/failed |

---

## 3. 风险点

| 风险 | 严重度 | 说明 |
|------|--------|------|
| LLM API 稳定性 | 中 | 100章连续调用可能因429/timeout中断，已增加crash recovery |
| sklearn 依赖 | 低 | TF-IDF adapter 在无 sklearn 环境下自动降级为 null |
| Windows symlink | 低 | 平台限制，CI 应在 Linux 运行 |
| CrewAI 遗留依赖 | 低 | 10个crewai相关测试被跳过，不影响核心功能 |

---

## 4. 本次新增文件

| 文件 | 类型 | 说明 |
|------|------|------|
| tests/test_derived_artifact_store.py | 测试 | B-01~B-03 |
| tests/test_governance_integration.py | 测试 | E-01~E-03 |
| tests/test_embedding_interrupt.py | 测试 | I-09 |
| scripts/run_stress_test.py | 脚本 | crash recovery 增强 |
| src/novel_workflow/schemas/manifest.py | Schema | DerivedArtifactStoreEntry |
| src/novel_workflow/validators/schema_validator.py | 校验 | 字段级验证 |
| src/novel_workflow/system_scripts/manifest_manager.py | 核心 | stage_write/promote |
| src/novel_workflow/system_scripts/governance_projection.py | 核心 | baseline 集成 |

---

## 5. 建议后续动作

1. 运行 100 章 LLM 验证（如本次跳过）
2. 更新 phase2_test_baseline.generated.md
3. 重新索引 codebase-memory
4. 考虑 Phase 4 CrewAI 迁移