# Phase 3 最终验收报告独立审计结论

**最终建议：不批准 Phase 3 正式完成。**

我未访问 GitHub，只审计了上传的 `proof_package.zip`。结论不是说所有实现都无效，而是：**当前验收报告存在多处证据缺失、路径不一致、测试不可复验、部分行号/数量声明不匹配**，不足以支撑“10/10 全部核实通过、无虚假声明”的结论。

---

## 1. 总体判定

| 审计项                   |              判定 | 说明                                                                               |
| --------------------- | --------------: | -------------------------------------------------------------------------------- |
| 压缩包完整性                |        **Fail** | 报告引用的多项文件不在压缩包内。                                                                 |
| 路径一致性                 |        **Fail** | 报告大量使用 `src/novel_workflow/...`，压缩包实际为扁平 `src/...`；需依赖 `FILE_MAP.txt` 才能对应。      |
| Phase2→Phase3 基线算术    |        **Pass** | 674→830，增量 +156，基线文档内部一致。                                                        |
| 新增 10 个测试文件是否齐全       |        **Fail** | 压缩包只包含 3/10 个新增测试文件。                                                             |
| `pytest tests/ -q` 复验 |        **Fail** | 本地执行失败：`ModuleNotFoundError: No module named 'novel_workflow'`。                  |
| 压力测试 JSON 数值          | **Mostly Pass** | §4 主要数值与 `stress_results.json` 匹配。                                               |
| 100 章压力测试完成声明         |  **Fail / 不充分** | JSON `passed=false`，缺少报告声称的 99 个 manuscript 文件；“transient timeout”原因无法从 JSON 证明。 |
| 关键代码行号                |     **Partial** | 多处匹配，但也有明显错位，如 MCP “NEVER applies” 不在报告声称的 line 68。                              |

---

## 2. §24 正式完成条件逐项判定

|  # | 条件                     |                           判定 | 审计说明                                                                                                                                                                                                                    |
| -: | ---------------------- | ---------------------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1 | 安全内核保护层                |                     **Fail** | `docs/kernel-boundary.md`、`scripts/scan_forbidden_paths.py` 存在，扫描脚本运行通过；但报告声称 `docs/kernel-boundary.md` 为 180 行，实际 **161 行**；`src/novel_workflow/guards/path_safety.py` 未在压缩包中提供，无法核实 PathSafetyGuard 实现；相关 `[T]` 不可复验。 |
|  2 | DerivedArtifactStore   |   **Fail / Partial GC Pass** | 按 `FILE_MAP` 映射后，`src/manifest.py:10-37`、`src/schema_validator.py:21-61`、`src/manifest_manager.py:162-182` 的核心类/方法存在；但原报告路径本身不存在，`pytest` 无法复验，且缺少完整包结构。                                                                |
|  3 | ChapterCommit          |                     **Fail** | `src/chapter_commit.py` 与 `src/projection_registry.py` 存在；但报告/基线中的 `tests/test_chapter_commit.py`、`tests/test_apply_chapter_commit.py` 未在压缩包中提供，`[T]` 不可复验。                                                             |
|  4 | BM25 + Retrieval Trace |   **Fail / Partial GC Pass** | `src/bm25_retriever.py`、`src/hybrid_retriever.py`、`src/retrieval.py:132-157` 存在，RetrievalTrace 字段匹配；但 `test_bm25_retriever.py`、`test_hybrid_retrieval.py` 缺失，测试不可复验。                                                    |
|  5 | Governance Shadow      |   **Fail / Partial GC Pass** | `GovernanceProjection` 存在，`audit`、`_generate_report`、shadow/active mode 可见；但测试失败，且依赖的完整模块未打包，运行级证明不足。                                                                                                                   |
|  6 | hard_pause 可选启用        |   **Fail / Partial GC Pass** | `governance_projection.py:250-269` 与 `pause_detector.py:17-25` 的 hard_pause 代码存在；但 `[T]` 不可复验。                                                                                                                          |
|  7 | Outbox                 |   **Fail / Partial FS Pass** | `src/outbox_store.py` 存在，能看到 enqueue、lease、heartbeat、retry、dead-letter、dedup 相关实现；但报告声称 `claim_with_lease`，实际方法名是 `claim_next`，且测试文件 `test_outbox_store.py` 缺失。                                                         |
|  8 | MCP 只读/propose-only    |                     **Fail** | `src/mcp_server.py` 存在，5 个 read tool + 1 个 propose tool 基本匹配；但报告称 `mcp_server.py:68` 有 “NEVER applies” 安全声明，实际 line 68 是 schema required 字段，`NEVER applies` 出现在约 line 224；`test_mcp_server.py` 缺失。                      |
|  9 | 作者工作台闭环                |   **Fail / Partial FS Pass** | `src/api.py` 存在，包含 7 个 `/api/...` endpoint，`tools/workbench.html` 有 6 个视图；但相关 e2e 测试缺失，`[T]` 不可复验。                                                                                                                      |
| 10 | 100 章验证通过              | **Fail / Data Partial Pass** | `stress_results.json` 与 `token_report.json` 存在，主要统计值匹配；但报告声称的 `tools/stress_llm_100/canon/manuscript/` 不存在；JSON 中 `passed=false`；无法从 JSON 证明 “1 LLM transient timeout”。                                                 |

---

## 3. 测试基线一致性

### 基线数字

| 指标      | Phase 2 | Phase 3 |   增量 | 判定                              |
| ------- | ------: | ------: | ---: | ------------------------------- |
| Total   |     674 |     830 | +156 | **Pass**                        |
| Passed  |     674 |     830 | +156 | **Pass as document claim only** |
| Failed  |       0 |       0 |    0 | **Not reproducible**            |
| Skipped |       0 |       0 |    0 | **Not reproducible**            |

基线文档的算术是正确的：`830 - 674 = 156`。

### 新增 10 个测试文件核对

| 测试文件                             | 基线声明测试数 | 压缩包内是否存在 |
| -------------------------------- | ------: | -------: |
| `test_derived_artifact_store.py` |      15 |        ✅ |
| `test_chapter_commit.py`         |      26 |        ❌ |
| `test_apply_chapter_commit.py`   |       6 |        ❌ |
| `test_bm25_retriever.py`         |      17 |        ❌ |
| `test_hybrid_retrieval.py`       |      24 |        ❌ |
| `test_governance_integration.py` |       9 |        ✅ |
| `test_outbox_store.py`           |      24 |        ❌ |
| `test_mcp_server.py`             |      13 |        ❌ |
| `test_e2e_integration.py`        |      17 |        ❌ |
| `test_embedding_interrupt.py`    |       5 |        ✅ |

**结论：新增 10 个测试文件只提供了 3 个，缺失 7 个。**

另外，主报告 §3 声称：

* Governance Integration：10 passed
  实际文件 AST 统计为 **9** 个测试函数。
* Embedding Interrupt：4 passed
  实际文件 AST 统计为 **5** 个测试函数。

这与 `FILE_MAP.txt` 和 Phase 3 baseline 中的 9 / 5 一致，但与主报告 §3 表格不一致。

---

## 4. 本地 pytest 复验结果

我在解压目录直接执行：

```bash
pytest -q --tb=short tests
```

结果为 **collection 阶段失败**：

```text
ModuleNotFoundError: No module named 'novel_workflow'
```

3 个已提供测试文件均因缺少 `novel_workflow` 包结构失败。压缩包中的源码是 `src/*.py` 扁平结构，但测试引用的是：

```python
from novel_workflow.schemas.manifest import ...
from novel_workflow.system_scripts.vector_adapter import ...
```

因此，报告中的以下 `[T]` 声明均无法由当前 proof package 复验：

* `830 passed`
* `133 passed`
* DerivedArtifactStore all pass
* Governance Integration all pass
* Embedding Interrupt all pass
* Outbox / MCP / BM25 / Hybrid / E2E 等测试通过声明

这不是“无 Python 环境”的问题，而是**证明包无法按报告命令运行**。

---

## 5. 压力测试数据核对

`stress_results.json` 的主要字段与报告 §4 基本一致：

| 指标                 |          报告声明 |    JSON 实际值 | 判定 |
| ------------------ | ------------: | ----------: | -- |
| `num_chapters`     |           100 |         100 | ✅  |
| `chapters` 数组长度    |            99 |          99 | ✅  |
| 成功章节               |            99 |  99 success | ✅  |
| 缺失章节               |         未具体列出 | `num=10` 缺失 | ⚠️ |
| `apply_errors`     |             0 |           0 | ✅  |
| `llm_errors`       |             1 |           1 | ✅  |
| `commit_count`     |            99 |          99 | ✅  |
| `total_tokens_in`  |        64,770 |      64,770 | ✅  |
| `total_tokens_out` |        79,200 |      79,200 | ✅  |
| `total_elapsed_ms` |     2,986,763 |   2,986,763 | ✅  |
| `passed`           | 报告异常说明称 false |       false | ✅  |

但有三点不充分：

1. 报告声称 `tools/stress_llm_100/canon/manuscript/` 下有 99 个 `.md` 文件，压缩包未提供该目录。
2. 报告称 “1 LLM transient timeout”，但 `stress_results.json` 只记录 `llm_errors=1`，没有 timeout / 429 / error detail。
3. 压力脚本自己的 `passed` 字段为 `false`，报告改用 5% 容限标准，但 proof package 中未提供 TEMP.md 原文来独立确认该标准。

---

## 6. 关键代码行验证摘要

| 报告声明                                                           | 审计结果                                                                            |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `manifest.py:10-37` `DerivedArtifactStoreEntry`                | ✅ 按映射到 `src/manifest.py` 后匹配。                                                   |
| `schema_validator.py:21-61` validators + register              | ✅ 匹配。                                                                           |
| `manifest_manager.py:162-182` `stage_write` / `promote_staged` | ✅ 行号匹配。                                                                         |
| `governance_projection.py:53-252`                              | ✅ 大体匹配，class line 53，`__init__` 实际 line 60，`check_hard_pause` line 250。         |
| `pause_detector.py:17-25` hard pause                           | ✅ 匹配。                                                                           |
| `retrieval.py:132-157` `RetrievalTrace`                        | ✅ 匹配。                                                                           |
| `mcp_server.py:68` “NEVER applies”                             | ❌ 不匹配；line 68 不是该声明，“NEVER applies” 在约 line 224。                                |
| `vector_adapter.py:91-103` `NullVectorAdapter`                 | ❌ 不匹配；line 91-103 属于 `TfidfVectorAdapter`，`NullVectorAdapter` 实际约 line 139-153。 |
| `tests/helpers.py:32-35` symlink skip                          | ✅ 匹配。                                                                           |
| `tests/helpers.py:39-45` CrewAI skip                           | ⚠️ 主体匹配，但实际文件只有 40 行，不存在 45 行。                                                  |

---

## 7. 主要不一致与缺失

1. **提交号不一致**
   用户审计基线与 `FILE_MAP.txt` 均写 `1951702`，但主报告写 `a5ad52a`，Phase 3 baseline 写 `18c963e`。这会削弱报告可追溯性。

2. **主报告路径与压缩包路径不一致**
   报告使用 `src/novel_workflow/...`，压缩包提供 `src/*.py`。虽然 `FILE_MAP.txt` 给了映射，但主报告的 `[FS]` 原始路径不能直接成立。

3. **测试证据严重不足**
   报告和 baseline 的 10 个新增测试文件中，压缩包只提供 3 个；本地 pytest 失败，无法支持 `830 passed`。

4. **报告 §5 声称存在的文件缺失**
   以下报告列出的文件未在压缩包中提供：
   `scripts/phase3_auto_runner.py`、`docs/phase3-acceptance-report-generated.md`、`docs/phase3-requirement-gap-analysis.md`、`docs/stress-test-100-chapters.md`。

5. **安全内核关键文件缺失**
   `src/novel_workflow/guards/path_safety.py` 未提供，无法核实 PathSafetyGuard。

6. **压力测试“通过”口径不稳定**
   JSON 自身 `passed=false`，报告改用 5% 容限，但缺少 TEMP.md 原文证明；同时 manuscript 文件目录未提供。

---

## 8. 最终审计意见

**不批准 Phase 3 正式完成。**

建议状态为：

```text
Phase 3 Final Acceptance: FAIL
原因：验收报告证据链不完整，测试不可复验，多项 [FS]/[GC]/[T] 声明存在缺失或不一致。
```

重新提交验收前，至少需要补齐：

1. 完整仓库结构或可直接运行的 proof package。
2. 7 个缺失的新增测试文件。
3. 可复现的 `pytest tests/ -q` 输出，或完整测试日志。
4. `PathSafetyGuard` 对应源码。
5. 压力测试 manuscript 产物目录，或移除该 `[FS]` 声明。
6. 修正主报告中的提交号、路径、行号、测试数量与 `passed=false` 口径说明。
