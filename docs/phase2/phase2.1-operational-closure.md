# Phase 2.1: Operational Closure

**Date:** 2026-05-30
**Base Commit:** 364cc5b
**Test Baseline:** 551 passed, 0 skipped, 0 failures

## 目标

把 Phase 2 已有组件收口为可追踪、可验证、可阻断、可回滚、可分阶段启用的运行时闭环。

## Wave 结构

| Wave | 目标 | 工作量 | 前置 |
|------|------|--------|------|
| 0 | 冻结执行基线 | S | 无 |
| 1 | Manifest/Generation/Rebuild 闭环 | L | W0 |
| 2 | Retrieval Active 运行时闭环 | L | W1 |
| 3 | Graph/Lifecycle/Drift/Structured Auditor 闭环 | L | W1+W2 |
| 4 | Arc Active + 长篇性能闭环 | L | W1-W3 |
| 5 | Gold Dataset + 最终验收 + Promotion | M | W3+W4 |

## Phase 3 Entry Gate（13 条件）

1. 所有 derived artifact 具备 generation lifecycle
2. 所有 builder 输出均自动登记 Manifest
3. stale/missing/hash mismatch 在 active mode 下 hard fail
4. rollback 后能按依赖关系完成 rebuild
5. Writer/Auditor/Extractor 使用独立 retrieval profile
6. retrieval_active 完成 staged promotion
7. arc_active 至少完成 shadow/dual-run/canary
8. 30/50 章 stress fixture 通过
9. Performance hard gate + trend gate 接入 CI
10. Structured Auditor 至少完成 dual-run + 回退路径
11. Character Drift streak escalation 完成
12. Drift gold dataset 具备首轮 precision/recall/fpr 指标
13. Change Gate 升级为行为级 Acceptance Matrix

## 禁止事项

- 不新增 Agent 类型
- 不引入复杂模型路由
- 不提前 fine-tuning
- 不同时全量启用 retrieval_active + arc_active
- 不允许 derived artifact 成为 source of truth
- 不允许 active mode silent fallback
- 不在无 rollback 验证下进入 full active
- 不跳过 30/50 章 stress gate
