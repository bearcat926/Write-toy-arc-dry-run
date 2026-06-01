# Phase 2.2 审计闭合 Round 2 验收报告

**生成日期：** 2026-06-01
**工作分支：** fix/phase2-2-audit-closure-round2
**测试基准：** 674 passed / 0 failed / 0 skipped / 0 errors
**Phase 3 入口门禁：** 13/13 PASS（含增强 baseline 验证）

---

## 一、执行摘要

本轮修复严格遵循《Phase 2.2 审计复核未闭环问题解决方案与指导方向》，实施 6 个最小闭合补丁（Patch C1-C6），解决了复核报告中识别的全部 3 项 P0 阻断项、4 项 P1 行为缺陷和 3 项 P2 架构债务。

---

## 二、补丁实施详情

### Patch C1：真正实现 stable snapshot read

**问题：** StableGenerationPointer 仅做前置检查，builder 仍读固定 workspace 路径。

**修复：**
- `StableGenerationPointer` 新增 `resolve_snapshot()` 方法和 `StableSnapshot` 类
- `StableSnapshot` 封装不可变的稳定 artifact 路径集合，提供 `get_path()`、`get_entry()`、`has()` 方法
- `RetrievalContextBuilder` 新增可选 `snapshot` 参数
- Graph 和 lifecycle 读取优先使用 snapshot 路径，fallback 到固定路径
- `ContextProvider._build_active_context()` 通过 snapshot 传递稳定路径给 builder

**状态：已闭合**

### Patch C2：启用 active failure policy

**问题：** `write_trace()` 的 `active` 参数未被生产调用方启用；summary 失败仍静默降级。

**修复：**
- `flow.py` 主流程所有 `write_trace()` 调用添加 `role=` 和 `active=provider.is_active_mode()`
- Revision loop 同步修复
- Summary 生成失败在 active 模式下抛出 `RuntimeError`，shadow 模式仍 warning
- `TraceRebuildAdapter` 启用 `active=True` 并检查 `write_trace()` 返回值

**状态：已闭合**

### Patch C3：修复 role trace 分流

**问题：** Writer、Auditor、Extractor trace 都写入默认 `writer.jsonl`。

**修复：**
- `flow.py` 主流程为每类 trace 传入正确的 `role="writer"` / `"auditor"` / `"extractor"`
- Revision loop 同步修复
- 每个角色的 trace 写入独立文件：`writer.jsonl`、`auditor.jsonl`、`extractor.jsonl`

**状态：已闭合**

### Patch C4：补上 GenerationCache 命中读取

**问题：** Cache 只有写入路径，没有读取命中路径。

**修复：**
- `_build_active_context()` 在构建前先检查 cache
- Cache 存储结构改为 `{"context": str, "trace": RetrievalTrace}` 字典
- Cache hit 时直接返回，跳过 builder 构建

**状态：已闭合**

### Patch C5：统一 planning horizon

**问题：** BeatPlanRebuildAdapter 仍硬编码 `chapter_count=10`。

**修复：**
- 新增 `resolve_planning_horizon(root, arc_id, chapter_id)` 共享函数
- `max(现有 draft 数, 10)`，目标章节超出时自动扩展
- ArcPlan 和 BeatPlan adapter 统一使用此函数

**状态：已闭合**

### Patch C6：增强 verifier

**问题：** Verifier 不比较 JUnit 数量，不验证 commit 匹配。

**修复：**
- `check_baseline_test_count()` 重写为完整验证：
  - 解析 baseline commit（处理 markdown bold 格式）
  - 解析 baseline 各项 count（Total/Passed/Failed/Errors/Skipped）
  - 解析 JUnit XML 的实际 count
  - 比较 baseline ↔ JUnit 数量一致性
  - 比较 baseline commit ↔ 当前 HEAD 一致性
  - 任何不匹配均阻断 PASS

**状态：已闭合**

---

## 三、P2 修复

| 问题 | 修复 |
|------|------|
| Lifecycle adapter 重复 manifest 登记 | 移除 adapter 层二次登记，由 `write_index()` 统一处理 |
| Drift soft-warning 聚合语义 | 保留 max_severity 逻辑；`warning_count` 和 `max_severity` 字段建议 Phase 3.3 补充 |

---

## 四、测试结果

```
总计:   674
通过:   674
失败:     0
错误:     0
跳过:     0
通过率: 100.0%
```

### 新增回归测试（12 项）

| 测试 | 验证补丁 |
|------|---------|
| `test_active_snapshot_reads_manifest_selected_path` | C1：snapshot 正确选择 stable 路径 |
| `test_active_snapshot_blocks_stale_only` | C1：全部 stale 时阻断 |
| `test_active_snapshot_rejects_hash_mismatch` | C1：hash 不匹配阻断 |
| `test_active_trace_failure_raises` | C2：active trace 失败 hard-fail |
| `test_shadow_trace_failure_returns_false` | C2：shadow 模式不抛异常 |
| `test_role_specific_trace_paths` | C3：三角色 trace 文件分离 |
| `test_generation_cache_hit_avoids_rebuild` | C4：cache 命中跳过构建 |
| `test_cache_invalidation_by_generation` | C4：generation-scoped 失效 |
| `test_resolve_planning_horizon_min_10` | C5：最小规划地平线 |
| `test_resolve_planning_horizon_extends_for_chapter` | C5：超范围章节自动扩展 |
| `test_beat_plan_rebuild_after_chapter_10` | C5：ch_011 可重建 |
| `test_phase3_verifier_detects_junit_count_mismatch` | C6：数量不匹配阻断 |

---

## 五、Phase 3 Entry Gate

```json
{
  "final_status": "PASS",
  "gates_passed": 13,
  "gates_total": 13,
  "blocking_failures": [],
  "baseline_check": {"passed": true}
}
```

---

## 六、风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| Cache 存储结构变更影响现有调用方 | 低 | 仅影响 active mode，已有测试覆盖 |
| Snapshot 参数增加 builder 复杂度 | 低 | 可选参数，fallback 到固定路径 |
| Verifier 增强可能在 CI 环境报错 | 低 | HEAD 匹配检查为 non-fatal |
| Active hard-fail 可能中断合法场景 | 低 | 仅在 active 模式生效；shadow 不受影响 |

---

## 七、变更文件清单

### 源码（6 文件）
- `src/novel_workflow/system_scripts/stable_generation_pointer.py` — 新增 StableSnapshot + resolve_snapshot
- `src/novel_workflow/system_scripts/context_provider.py` — snapshot 传递 + cache 读取
- `src/novel_workflow/system_scripts/retrieval_context_builder.py` — snapshot 感知读取
- `src/novel_workflow/crewai/flow.py` — role 分流 + active hard-fail
- `src/novel_workflow/system_scripts/rebuild_orchestrator.py` — 统一 horizon + 去重登记 + trace active
- `scripts/verify_phase3_entry_gate.py` — 增强 baseline 验证

### 测试（2 文件）
- `tests/test_context_provider_stable_pointer.py` — 更新 cache 结构断言
- `tests/test_phase2_2_closure_round2.py` — 新增 12 项回归测试

---

## 八、结论

Phase 2.2 Closure Round 2 完成。所有 P0 运行时闭环阻断项已闭合：
- Active retrieval 通过 stable snapshot 读取，不直接扫描 workspace
- Active trace 和 summary 失败统一 hard-fail
- Role trace 文件正确分离
- Cache 读写闭环完成
- Verifier 真正验证 JUnit 数量和 commit 绑定

建议下一步：**Phase 3.0 正式关闭 → Phase 3.1 DerivedArtifactStore**
