# Novel Workflow — AI 长篇小说创作控制面

> **Agent 可以越来越聪明，但永远不会越来越有权力。**

一个基于 `novel-workflow` 控制协议 + CrewAI 执行编排的长篇小说创作系统。不是让 AI 自动写完整本书，而是让 AI 在严格的事实协议内高质量提案，人类作者保留最终审批权。

## 这解决什么问题

现有 AI 写作工具的根本问题：

| 问题 | 本系统的解法 |
|---|---|
| Agent 直接修改 canon，事实漂移 | Agent 只能写 drafts/reviews/proposals，不能写 canon/ledgers |
| 长篇角色关系崩坏 | 结构化 ledger（timeline, character_knowledge, foreshadowing）追踪叙事状态 |
| AI 自说自话完成 | 三类 Human Gate（方向/弧开始/弧结束），作者审批留 evidence |
| 一次生成全书，质量失控 | 逐章循环：Writer → Auditor → Extractor → 系统脚本 merge |
| 事实污染，无法回滚 | atomic apply + snapshot rollback + consumed 防重复 |

## 架构

```text
作者审批层          ← 最终决策权，gate records 必须有 author evidence
    ↓
事实源层            ← canon/ + ledgers/，唯一长期叙事事实源
    ↓
弧内工作层          ← arc_working_state（临时 overlay，不等于 canon）
    ↓
执行编排层 CrewAI   ← Writer / Auditor / Extractor Agent
    ↓
系统脚本层          ← schema validation, atomic apply, rollback, pause
    ↓
派生层              ← dashboard, RAG index, progress（derived，非事实源）
```

**权限边界：**
- Agent 可读：canon, ledgers, arc_working_state, chapter context
- Agent 可写：drafts, reviews, proposals（通过 PathSafetyGuard 强制）
- Agent 禁写：canon, ledgers, arc_working_state, ledger_diff, gates
- 系统脚本是受控状态落盘权唯一持有者

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/bearcat926/Write-toy-arc-dry-run.git
cd Write-toy-arc-dry-run

# 2. 安装
pip install -e ".[dev]"

# 3. 运行测试
pytest tests/ -v

# 4. LLM dry run（需要 API key）
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://your-endpoint/v1"
export OPENAI_MODEL_NAME="your-model"
python run_llm_dry_run.py
```

## 测试覆盖

```bash
pytest tests/ -v
# 312+ passed, 5 skipped (Windows symlink tests), covering:
# - DoD #1: Agent write rejection (path safety)
# - DoD #2: Gate evidence enforcement
# - DoD #3: Proposal cannot directly apply
# - DoD #4: Plugin default deny
# - DoD #7: Atomic apply + rollback + idempotent
# - DoD #8: Schema versioning
# - DoD #10: Path traversal / symlink escape
# - Phase 2: Provenance enforcement, derived path hardening, CI auditability
```

## MVP vs Production Roadmap

| 能力 | MVP (done) | Production (planned) |
|---|---|---|
| Schema validation | Single version | Migration protocol |
| Concurrency | Single process, reject parallel | File locks + timeout |
| Rollback | Full snapshot | Fine-grained inverse diff |
| Plugins | Runtime disabled | Full permission system |
| Ledgers | timeline, knowledge, foreshadowing | + relationship, emotion_arc |
| CrewAI | Agent.kickoff() + direct save | Tool-based calling + Flow |
| Pause | Single type | hard_pause / creative_review / soft_warning |

## 核心原则

1. **强化 Agent 能力，不强化 Agent 权限** — Agent 可以更会写、更会审、更会提案，但永远不能更会"批准"
2. **canon/ledger 单一事实源** — dashboard、RAG、progress 都是派生层，不能替代事实
3. **作者审批驱动** — 系统脚本不能替作者批准 gate records
4. **atomic apply** — canonicalize draft + apply ledger_diff 必须同成功同失败

## 项目结构

```
src/novel_workflow/
├── schemas/          # Pydantic models (gate, proposal, ledgers, arc_state, diff, progress)
├── validators/       # schema_validator, gate_validator, proposal_validator
├── guards/           # path_safety (PathSafetyGuard), lock_manager
├── system_scripts/   # arc_state_manager, ledger_diff_generator, canonicalizer, atomic_apply_manager
├── pause/            # pause_detector
├── crewai/           # agents, tools (safe_write_*), flow (run_novel_flow)
├── config.py         # schema versions, allowlists, retry policy, pause taxonomy
└── project_init.py   # directory structure initialization
```

## License

MIT
