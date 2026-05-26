## Context

PLAN.md 已定稿完整的 CrewAI × novel-workflow 融合架构，包含：
- 七层架构（作者审批层、事实源层、弧内工作层、执行编排层、系统脚本层、派生层、插件生态层）
- 权限模型：Agent 只写 drafts/reviews/proposals，系统脚本是受控状态落盘权唯一持有者
- 10 条 DoD，分为不可妥协边界 / MVP 简化 / 规模化增强
- MVP profile：单进程、插件禁用、full snapshot rollback、单 schema version
- 完整文件协议（Section 11）、proposal schema（含 source/evidence 必填）、pause taxonomy
- arc_working_state 作为 arc overlay（高时效性，非高权威）、canon/manuscript 正文落盘

当前状态：零代码，需要从架构文档落地为可运行的系统脚本层。

## Goals / Non-Goals

**Goals:**
- 用 Python 实现系统脚本层核心组件，可独立运行
- 用 fixture 驱动的 pytest 测试覆盖 PLAN.md Section 13 全部验收场景
- 验证控制闭环：gate → draft → review → proposal → merge → ledger_diff → atomic apply → canon/manuscript
- 验证安全边界：path escape 拒绝、proposal 缺 evidence 拒绝、重复 apply 拒绝、Agent 禁写拒绝

**Non-Goals:**
- 不接 CrewAI（dry run 用 fixture 模拟 Agent 输出）
- 不实现插件运行时
- 不实现多进程锁（单进程拒绝并发即可）
- 不实现 inverse diff（full snapshot rollback 即可）
- 不实现 schema migration（单版本 + unknown 拒绝即可）
- 不实现完整 dashboard
- 不实现 RAG index

## Decisions

### D1: 语言和框架

**选择**: Python 3.11+、Pydantic v2、pytest

**理由**:
- CrewAI 是 Python 生态，后续集成零摩擦
- Pydantic v2 提供 schema validation、JSON Schema 导出、类型安全
- pytest fixture 机制天然适合 dry run 测试

**替代方案**: TypeScript（CrewAI 无 TS SDK）、Go（生态不匹配）

### D2: 项目结构

**选择**: 按 PLAN.md Section 11 文件协议组织，Python 包放在 `src/novel_workflow/`

```
project_root/
├── src/novel_workflow/
│   ├── schemas/          # Pydantic models for all JSON/JSONL artifacts
│   ├── validators/       # schema validator, proposal validator, gate validator
│   ├── system_scripts/   # merger, diff generator, canonicalizer, apply manager
│   ├── guards/           # path safety guard, lock manager
│   ├── pause/            # emergency pause detector
│   └── config.py         # allowlist, schema versions, retry policy
├── tests/
│   ├── fixtures/         # toy arc fixture data
│   ├── test_dod_*.py     # 每个 DoD 一个测试文件
│   └── test_e2e_*.py     # 端到端验收场景
├── toy_project/          # dry run 运行时目录（fixture 初始化）
└── pyproject.toml
```

### D3: Schema 定义方式

**选择**: Pydantic models 作为 single source of truth，运行时用 `model_validate()`，测试时用 `model_json_schema()` 验证 fixture 格式

**理由**:
- 一个定义同时服务 validation 和 documentation
- Pydantic v2 性能好，dry run 无需外部 schema store

### D4: Atomic apply 实现

**选择**: 目录级 rename（先写到 staging/，apply 时 rename 到目标路径）+ full snapshot 备份

**理由**:
- rename 在同一文件系统上是原子操作
- full snapshot 对 MVP（3 章 toy arc）足够简单可靠
- 不需要数据库或 WAL

### D5: Lock 策略（MVP）

**选择**: 进程内 threading.Lock，单进程单任务，显式拒绝并发

**理由**:
- MVP profile 明确要求单进程
- 为 Production profile 预留 lock 接口，后续替换为文件锁

### D6: Pause taxonomy

**选择**: MVP 即定义 `hard_pause | creative_review | soft_warning` enum，在 pause_report.jsonl 中记录

**理由**:
- 安全错误和创作疑点必须分开记录
- 数据从第一版积累，后续做 pause 频率分析
- 实现成本极低（一个 enum 字段）

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| fixture 模拟不够真实，可能漏掉 LLM 输出的边界 case | dry run 验证的是系统脚本层正确性，不是 Agent 质量；后续 CrewAI 集成时再补 Agent 边界测试 |
| 目录级 rename 在跨文件系统时不原子 | MVP 要求 toy_project 在同一文件系统内；Production 用数据库或 WAL |
| Pydantic v2 的 JSON Schema 输出与 PLAN.md 中的 schema 定义可能漂移 | 测试中对比 Pydantic schema 与 PLAN.md 文档，发现漂移即修复 |
| arc_working_state overlay 与 canon 冲突检测依赖数据比对，可能遗漏语义冲突 | MVP 只做结构冲突检测（同 key 不同 value），语义冲突留给后续 LLM 审计 |
