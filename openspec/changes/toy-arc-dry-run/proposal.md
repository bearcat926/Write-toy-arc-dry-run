## Why

PLAN.md 中已定稿 CrewAI × novel-workflow 融合架构，包含完整的权限模型、10 条 DoD、MVP profile、文件协议和验收场景。架构文档已完成多轮评审并修正了全部已知问题。下一步是通过 non-LLM dry run 验证控制闭环是否可落地——不接 CrewAI，用 fixture 模拟 draft/review/proposal，验证系统脚本层的正确性。

## What Changes

- 新建 Python 项目骨架，按 PLAN.md Section 11 文件协议组织目录
- 实现系统脚本层核心组件：schema validator、proposal validator、arc_working_state merger、ledger_diff generator、canonicalizer、atomic apply manager、lock manager、path safety guard、emergency pause detector
- 实现 3 个 ledger 的最小 schema：timeline、character_knowledge、foreshadowing
- 实现 gate record validator（含 author_input_evidence 检查）
- 实现 proposal validator（含 source/evidence 必填、operation enum、ledger-specific schema）
- 实现 path safety guard（normalize + allowlist + symlink 检测）
- 编写 fixture 驱动的端到端测试，覆盖 PLAN.md Section 13 全部验收场景
- 暂不实现：CrewAI 集成、插件运行时、完整 dashboard、多进程锁、inverse diff、migration

## Capabilities

### New Capabilities
- `control-plane`: 系统脚本层——schema validation、gate validation、proposal validation、atomic apply、rollback、pause detection
- `file-protocol`: 按 PLAN.md Section 11 实现的项目文件结构、path safety、allowlist
- `ledger-system`: 3 个 ledger（timeline、character_knowledge、foreshadowing）的 schema 定义、merge 策略、diff 生成
- `arc-state-management`: arc_working_state 初始化、merge、status 标记、依赖级联失效
- `dry-run-fixtures`: fixture 数据和端到端验收测试

### Modified Capabilities
（无，这是全新项目）

## Impact

- 新建 Python 项目，无既有代码影响
- 依赖：pytest、pydantic（schema validation）、pathlib（path safety）
- 产出可独立运行的系统脚本层，后续 CrewAI 集成只需对接 tool allowlist
