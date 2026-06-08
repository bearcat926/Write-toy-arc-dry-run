# Phase 3 独立审计提示词

将此提示词与 proof_package.zip 一起发送给审计模型。

---

## 审计任务

你是独立审计师。请对 Write-toy-arc-dry-run 项目的 Phase 3 最终验收报告进行全面审计。

## 源码仓库

GitHub: https://github.com/bearcat926/Write-toy-arc-dry-run  
审计基线提交: 1951702 (main branch)  
**注意**: 所有证明材料已打包在 proof_package.zip 中。无需访问远程仓库。

---

## 压缩包结构

解压 proof_package.zip 后，你会看到以下结构：

```
phase3-final-acceptance-report.md    ← 主报告，审计起点
├── docs/
│   ├── phase2_test_baseline.generated.md   ← Phase 2 基线 (674 tests)
│   ├── phase3_test_baseline.generated.md   ← Phase 3 基线 (830 tests)
│   └── kernel-boundary.md                  ← 安全边界文档
├── src/
│   ├── manifest.py               ← DerivedArtifactStoreEntry (B-01)
│   ├── schema_validator.py       ← 字段级验证 (B-03)
│   ├── manifest_manager.py       ← stage_write/promote_staged (B-02)
│   ├── governance_projection.py  ← GovernanceProjection (E-02/E-03)
│   ├── chapter_commit.py         ← ChapterCommit Schema (C-01)
│   ├── projection_registry.py    ← Projection Registry (C-03)
│   ├── bm25_retriever.py         ← BM25 + FTS5 (D-01/D-02)
│   ├── hybrid_retriever.py       ← RRF + Profiles + Trace (D-06~D-10)
│   ├── outbox_store.py           ← Outbox (F-01~F-07)
│   ├── mcp_server.py             ← MCP Server (G-05/G-06)
│   ├── api.py                    ← Workbench API (H-01~H-07)
│   ├── retrieval.py              ← RetrievalTrace Schema (D-10)
│   ├── pause_detector.py         ← EmergencyPauseDetector (E-08)
│   └── vector_adapter.py         ← NullVectorAdapter (I-09)
├── scripts/
│   ├── scan_forbidden_paths.py   ← 路径扫描器 (A-02)
│   └── run_stress_test.py        ← 100章压力测试脚本
├── tools/
│   └── workbench.html            ← 作者工作台 SPA (H-02~H-07)
├── tests/
│   ├── test_derived_artifact_store.py   ← B-01~B-03 测试
│   ├── test_governance_integration.py   ← E-01~E-03 测试
│   ├── test_embedding_interrupt.py      ← I-09 测试
│   └── helpers.py                       ← skip标记 (symlink/crewai)
├── stress_results.json           ← 100章压力原始数据 (99 chapters)
└── token_report.json             ← 逐章token明细
```

## 主报告章节结构

报告 `phase3-final-acceptance-report.md` 包含以下章节：

| § | 标题 | 审计重点 |
|---|------|---------|
| 1 | §24 正式完成条件（10/10） | 每项条件是否有对应文件？文件是否存在？ |
| 2 | 测试基线演进（Phase2→Phase3） | 674→830 (+156) 是否一致？新增10文件是否都在压缩包内？ |
| 3 | 测试通过率 | 830 passed 是否可复验？(需在本地环境运行pytest) |
| 4 | 100章LLM压力测试 | 对照 stress_results.json 逐项核对数值 |
| 5 | Phase 3 新增代码变更 | 文件数量和内容是否匹配？ |
| 6 | 风险点 | 风险评估是否合理？ |
| 7 | §22 Ready Queue 完成状态 | 逐批核对 A~I 系列 |
| 8 | §24 最终判定 | 独立给出你的 Pass/Fail 判定 |
| 9 | 核实异常说明 | 报告如实标注异常，审查是否遗漏？ |
| 10 | 仍处于实验状态 | 推迟项是否合理？ |
| 11 | 结论 | Phase 3 是否可以正式宣布完成？ |

## 审计要求

1. **逐条核实**: 报告中每条带 `[FS]`/`[GC]`/`[T]` 标签的声明，对照压缩包内对应文件核实。
2. **压力数据核对**: 打开 `stress_results.json`，逐字段与报告 §4 表格比对。
3. **基线一致性**: 对比 `phase2_test_baseline.generated.md` (674) 和 `phase3_test_baseline.generated.md` (830)，计算增量是否正确。
4. **代码关键行验证**: 对报告中标注了具体行号的方法/类（如 `manifest.py:10-37`），打开对应文件确认行号匹配。
5. **产出**: 一份结构化审计报告，包含：
   - 每条 §24 条件的 Pass/Fail/Unable-to-verify 判定
   - 发现的任何不一致或缺失
   - 最终建议：是否批准 Phase 3 完成

## 注意事项

- **不要**访问 GitHub — 所有代码和测试已在压缩包内。
- 报告中标注的路径均为项目相对路径，与压缩包内结构一致。
- `[FS]` = 文件存在性验证, `[GC]` = 代码内容grep验证, `[T]` = 测试执行验证（T类需本地pytest环境）
- 如无法执行 pytest（无Python环境），请标注为 `Unable-to-verify [T]: requires local pytest execution` 并基于其他证据推断。
