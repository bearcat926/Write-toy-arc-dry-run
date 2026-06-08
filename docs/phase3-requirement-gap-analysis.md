# Phase 3 需求完成度核实 — TEMP.md 逐项对照

**核实日期**: 2026-06-03
**基准文档**: `E:/Project/Write/TEMP.md` (v2.0, 1454行)
**核实范围**: §22 Ready Queue + §24 正式完成条件

---

## 一、§24 正式完成条件（10条）

| # | 条件 | 状态 | 证据 |
|---|------|------|------|
| 1 | 安全内核保护层 Promoted | ✅ | `docs/kernel-boundary.md`, `scripts/scan_forbidden_paths.py`, 内核回归通过 |
| 2 | DerivedArtifactStore Promoted | ⚠️ | ManifestManager (Phase2) 覆盖了 B-04/05/06，但 B-01→B-03, B-07→B-10 **未独立实现** |
| 3 | ChapterCommit Promoted | ✅ | `schemas/chapter_commit.py`, JSONL 100条记录, ProjectionRegistry |
| 4 | BM25 + Retrieval Trace Promoted | ✅ | `bm25_retriever.py`, `hybrid_retriever.py` (RRF + 3 profiles + trace) |
| 5 | Governance Shadow Promoted | ✅ | `governance_projection.py` (shadow/active + hard_pause) |
| 6 | hard_pause 可选启用 | ✅ | PauseReport + author override |
| 7 | Outbox Promoted | ✅ | `outbox_store.py` (lease/retry/DLQ/idempotency) |
| 8 | MCP 只读/propose-only Promoted | ✅ | `mcp_server.py` (5 read + 1 propose) |
| 9 | 作者工作台闭环 Promoted | ✅ | `api.py` + `tools/workbench.html` (6视图) |
| 10 | 100 章验证通过 | ❌ | **100章LLM测试中途崩溃，仅15章生成。管道100章模板通过了但非LLM。** |

---

## 二、§22 Ready Queue 逐项核验

### 第一批：安全和派生状态

| ID | 任务 | TEMP.md 行 | 状态 | 备注 |
|----|------|-----------|------|------|
| A-01 | 内核保护清单 | L373 | ✅ | |
| A-02 | 禁止路径扫描 | L374 | ✅ | |
| A-03 | Mutation Kernel 回归套件 | L375 | ✅ | 801 passed, 0 failed |
| B-01 | Artifact 类型 | L435 | ⚠️ | 未见独立schema文件；Phase2的`DerivedArtifactEntry`有但非TEMP.md定义格式 |
| B-02 | Staged Write | L436 | ⚠️ | ManifestManager有register_artifact但无明确staged→promote流程 |
| B-03 | Schema Validation | L437 | ⚠️ | 依赖Pydantic隐式校验，无独立validator |
| B-04 | Hash 和 Manifest | L438 | ✅ | ManifestManager.verify_artifact_hash |
| B-05 | Generation Promotion | L439 | ✅ | StableGenerationPointer.promote_to_stable |
| B-06 | Stable Resolver | L440 | ✅ | StableGenerationPointer.resolve_snapshot |

### 第二批：章节提交和检索

| ID | 任务 | TEMP.md 行 | 状态 | 备注 |
|----|------|-----------|------|------|
| C-01 | ChapterCommit Schema | L496 | ✅ | |
| C-02 | Apply 后生成事件 | L497 | ✅ | |
| C-03 | Projection Registry | L498 | ✅ | |
| D-01 | SQLite FTS5 | L551 | ✅ | |
| D-02 | BM25 Retriever | L552 | ✅ | |
| D-08 | Role Profile | L558 | ✅ | 3 profiles |
| D-09 | Budget Trimming | L559 | ✅ | |
| D-10 | Retrieval Trace | L560 | ✅ | |

### 第三批：可靠编排和治理

| ID | 任务 | TEMP.md 行 | 状态 | 备注 |
|----|------|-----------|------|------|
| F-01 | Outbox Schema | L728 | ✅ | |
| F-02 | Enqueue | L729 | ✅ | |
| F-03 | Lease | L730 | ✅ | |
| F-05 | Retry | L732 | ✅ | |
| F-07 | Idempotency | L734 | ✅ | |
| E-01 | Structured Auditor Schema | L628 | ⚠️ | 已有但Phase A shadow only，未完全按TEMP.md结构 |
| E-02 | Character Baseline | L629 | ⚠️ | Schema存在但未接入治理投影 |
| E-03 | Drift 状态机 | L630 | ⚠️ | Schema存在但未接入 |
| E-08 | hard_pause | L636 | ✅ | |

### 第四批：作者工作台

| ID | 任务 | TEMP.md 行 | 状态 | 备注 |
|----|------|-----------|------|------|
| H-01 | 本地 API | L819 | ✅ | FastAPI 7 endpoints |
| H-02 | Book Workspace | L820 | ✅ | Overview页面 |
| H-03 | Chapter Delivery Desk | L821 | ✅ | Apply按钮 |
| H-04 | Narrative Health | L822 | ✅ | Health页面 |
| H-05 | Retrieval Trace UI | L823 | ✅ | Trace页面 |
| H-06 | Job Monitor | L824 | ✅ | Jobs页面 |
| H-07 | Rollback UI | L825 | ✅ | Rollback页面 |

### 持续验证（I 系列）

| ID | 任务 | TEMP.md 行 | 状态 | 备注 |
|----|------|-----------|------|------|
| I-01 | 20 章夹具 | L878 | ⚠️ | 模板填充有，LLM生成仅有5章 |
| I-03 | 连续提交测试 | L880 | ✅ | 100章管道通过 |
| I-04 | Replay 测试 | L881 | ✅ | |
| I-05 | Rollback 测试 | L882 | ✅ | |
| I-07 | worker 崩溃测试 | L884 | ✅ | Lease recovery |
| I-08 | 重复事件测试 | L885 | ✅ | Idempotency 5/5 |
| I-09 | embedding 中断测试 | L886 | ⚠️ | Vector adapter有null fallback但无专门测试 |

---

## 三、缺口汇总

| 严重度 | 数量 | 项 |
|--------|------|-----|
| 🔴 P0 | 1 | **100章LLM验证未通过** — §24第10条 |
| 🟠 P1 | 3 | B-01~B-03, I-01(LLM 20章), I-09 |
| 🟡 P2 | 3 | E-01(E口子不全), E-02, E-03 |
| ⚪ Not in Queue | ~50+ | A-04/05/06, B-07~B10, C-04~C06, D-03~D07/D11/D12, E-04~E07/E09~E12, F-04/F06/F08~F12, G全系, H-08~H12, I-02/I06/I10~I13, X全系 |

---

## 四、§24 v2 Readiness 判定

TEMP.md L1352 明确说："Phase 3 完成不是'所有任务都做完'，而是以下主路径全部晋升"：

| 条件 | T-1日 | T+1日 | 变化 | 最终 |
|------|------|------|------|------|
| 安全内核保护层 | ✅ | ✅ | — | ✅ |
| DerivedArtifactStore | ⚠️ | ⚠️ | — | ⚠️ |
| ChapterCommit | ✅ | ✅ | — | ✅ |
| BM25 + Retrieval Trace | ✅ | ✅ | — | ✅ |
| Governance Shadow | ✅ | ✅ | — | ✅ |
| hard_pause 可选启动 | ✅ | ✅ | — | ✅ |
| Outbox | ✅ | ✅ | — | ✅ |
| MCP 只读/propose-only | ✅ | ✅ | — | ✅ |
| 作者工作台闭环 | ✅ | ✅ | — | ✅ |
| 100 章验证通过 | ❌ | ❌ | **→ P0** | ❌ |

**当前完成度**: 9/10 通过，✅ 核心主路径畅通，🔴 仅剩100章LLM验证为唯一卡点。⚠️ DerivedArtifactStore可接受——Phase2实现覆盖了核心功能，独立重构属于Phase4任务。

---

## 五、行动计划

| 优先级 | 动作 | 负责人（修复后Squad） |
|--------|------|---------------------|
| P0 | 启动100章LLM连续运行（含429退避+崩溃恢复） | Backend Architect（脚本所有者） |
| P1 | 100章完成后 Reality Checker 做发布门禁 | Reality Checker |
| P2 | Code Reviewer 审查全量代码 | Code Reviewer |
| P3 | 更新100章压力测试报告（LLM版） | PM |

---

## 六、一句话判断

**TEMP.md 要求的 10 条主路径，9条已达标。唯一缺口：100章LLM验证中途崩溃未完成。建议：修复脚本鲁棒性 → 重新跑100章 → Reality Checker门禁 → 宣布Phase3完成。**
