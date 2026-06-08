# Phase 3 最终验收报告 — 审计提示词

将此提示词与 `proof_package.zip` 一并发送给待审计模型。

---

## 审计角色

你是独立技术审计师。对 `phase3-final-acceptance-report.md` 中的全部声明进行独立验证。

---

## 材料来源

**GitHub 源码仓库**: `https://github.com/bearcat926/Write-toy-arc-dry-run`  
**审计基线提交**: `7cfd9d4` (main)  
**⚠ 不要访问远程仓库**。所有证明文件已打包在 `proof_package.zip` 中。远程仓库仅用于溯源参考。

---

## 压缩包结构

```
proof_package.zip
├── phase3-final-acceptance-report.md   ← 主报告（审计目标文件）
├── FILE_MAP.txt                        ← 报告路径 → 包内路径映射表
├── stress_results.json                 ← 100章压力测试原始数据（99章）
├── token_report.json                   ← 逐章 token 消耗明细
├── src/                                ← 核心源码（15个文件）
│   ├── manifest.py                     ← §1条件2: DerivedArtifactStoreEntry
│   ├── schema_validator.py             ← §1条件2: 字段级验证
│   ├── manifest_manager.py             ← §1条件2: stage_write/promote_staged
│   ├── governance_projection.py        ← §1条件5/6: Governance + hard_pause
│   ├── chapter_commit.py               ← §1条件3: ChapterCommit schema
│   ├── projection_registry.py          ← §1条件3: Projection registry
│   ├── bm25_retriever.py               ← §1条件4: BM25/FTS5
│   ├── hybrid_retriever.py             ← §1条件4: RRF + 3 profiles
│   ├── retrieval.py                    ← §1条件4: RetrievalTrace schema
│   ├── outbox_store.py                 ← §1条件7: Outbox
│   ├── mcp_server.py                   ← §1条件8: MCP server
│   ├── api.py                          ← §1条件9: Workbench API
│   ├── pause_detector.py               ← §1条件6: EmergencyPauseDetector
│   ├── vector_adapter.py               ← §6: NullVectorAdapter
│   └── path_safety.py                  ← §1条件1: PathSafetyGuard
├── tests/                              ← 测试文件（11个文件）
│   ├── test_derived_artifact_store.py
│   ├── test_governance_integration.py
│   ├── test_embedding_interrupt.py
│   ├── test_chapter_commit.py
│   ├── test_apply_chapter_commit.py
│   ├── test_bm25_retriever.py
│   ├── test_hybrid_retrieval.py
│   ├── test_outbox_store.py
│   ├── test_mcp_server.py
│   ├── test_e2e_integration.py
│   └── helpers.py
├── docs/                               ← 文档（5个文件）
│   ├── phase2_test_baseline.generated.md
│   ├── phase3_test_baseline.generated.md
│   ├── kernel-boundary.md
│   └── TEMP_excerpt.md                  ← §24/§22 阈值依据
├── scripts/
│   ├── scan_forbidden_paths.py
│   └── run_stress_test.py
├── tools/
│   └── workbench.html
└── manuscript/                          ← 99章 LLM 生成内容（ch_001~ch_100, 缺ch_010）
```

---

## 审计清单

### A. §24 完成条件（主报告 §1）

逐条打开包内对应源码文件，核实：
- 文件是否存在
- 报告声称的类/方法/行号是否匹配
- 特别关注修正后的行号：`mcp_server.py:224`、"NEVER applies" 在 docstring；`vector_adapter.py:139-153`；`helpers.py:39-40`

### B. 测试基线（主报告 §2）

打开 `docs/phase2_test_baseline.generated.md` 和 `docs/phase3_test_baseline.generated.md`：
- 674→830 增量是否为 +156
- 新增 10 个测试文件是否全部在包内 `tests/` 目录
- 每个文件声明的测试数量与包内文件一致（[A] 列第 9 测试 = 9，[B] 列第 5 测试 = 5）

### C. 100章压力测试（主报告 §4）

对 `stress_results.json` 进行字段级核对：
- `num_chapters=100`, chapters 数组长度=99, `apply_errors=0`, `llm_errors=1`
- `total_tokens_in=64770`, `total_tokens_out=79200`, `total_elapsed_ms=2986763`
- `passed=false`（已在报告 §9 透明标注）

### D. 内容质量（主报告 §4 小节）

抽样阅读 `manuscript/ch_001.md`, `ch_050.md`, `ch_100.md`：
- 叙事是否连贯？角色是否一致？
- 世界构建（Valdris→Nordmark, Sunstrider, Shadow Council, Obsidian Heart）是否跨章延续？
- 是否存在模板复读或质量退化？

### E. 路径映射

报告使用原始项目路径（如 `src/novel_workflow/schemas/manifest.py`），包内为扁平路径（`src/manifest.py`）。使用 `FILE_MAP.txt` 进行对应。

---

## 审计输出格式

```
# Phase 3 验收报告 — 审计结论

## 总体判定: [APPROVED / CONDITIONAL / REJECTED]

## §24 逐项判定
| # | 条件 | 判定 | 证据 |
|---|------|------|------|

## 数据一致性
- 测试基线: [Pass/Fail]
- 100章压力: [Pass/Fail]
- 压力数据: [逐项匹配/不匹配列表]

## 内容质量评估
- 叙事一致性: [/5]
- 角色发展: [/5]
- 世界观: [/5]
- 退化检测: [有/无]

## 发现的不一致
- [列表]

## 建议
```
