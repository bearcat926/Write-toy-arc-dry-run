---
comet_change: toy-arc-dry-run
role: technical-design
canonical_spec: openspec
---

# Design Doc: toy-arc-dry-run

## 模块架构

```text
src/novel_workflow/
├── schemas/                    # Pydantic models (single source of truth)
│   ├── __init__.py
│   ├── common.py               # schema_version 基类、timestamp mixin
│   ├── gate.py                 # GateRecord, DirectionGate, ArcStartGate, ArcEndGate
│   ├── proposal.py             # LedgerUpdateProposal (含 per-ledger operation enum)
│   ├── diff.py                 # LedgerDiff, CanonDiff, ApplyRecord
│   ├── arc_state.py            # ArcWorkingState, ArcWorkingStateEntry
│   ├── ledgers.py              # TimelineEvent, CharacterKnowledgeEntry, ForeshadowEntry
│   ├── chapter.py              # ChapterEffectReport
│   └── progress.py             # ProgressEntry, PauseReport
├── config.py                   # SUPPORTED_SCHEMA_VERSIONS, ALLOWLIST, RETRY_POLICY, pause taxonomy enum
├── validators/
│   ├── __init__.py
│   ├── schema_validator.py     # schema_version 存在性 + 支持性
│   ├── gate_validator.py       # author_input_evidence + approval_level
│   └── proposal_validator.py   # source/evidence 必填 + operation enum + error 分类
├── guards/
│   ├── __init__.py
│   ├── path_safety.py          # normalize + allowlist + symlink 检测
│   └── lock_manager.py         # threading.Lock + finally 释放
├── system_scripts/
│   ├── __init__.py
│   ├── arc_state_manager.py    # init + merge + cascade invalidate
│   ├── ledger_diff_generator.py # per-ledger merge 策略
│   ├── canonicalizer.py        # drafts → canon/manuscript
│   └── atomic_apply_manager.py # 全流程编排（含 snapshot + rollback）
├── pause/
│   ├── __init__.py
│   └── pause_detector.py       # 分类 hard_pause / creative_review / soft_warning
└── project_init.py             # toy_project 目录初始化
```

## 关键接口

### AtomicApplyManager.apply()

全流程单入口，PLAN.md Section 8 伪代码的 Python 实现：

```python
def apply(
    self,
    arc_id: str,
    gate_record: GateRecord,
    drafts: list[Path],
    ledger_diff: LedgerDiff,
    canon_diff: CanonDiff | None,
    project_root: Path,
) -> ApplyResult:
    # 1. validate gate record
    # 2. validate schema versions
    # 3. lock
    # 4.   validate not consumed
    # 5.   prepare rollback snapshot (full copy to archive/)
    # 6.   canonicalize drafts → canon/manuscript/
    # 7.   apply ledger_diff → update ledgers/
    # 8.   apply canon_diff → update canon/characters/ (if exists)
    # 9.   write apply_record
    # 10.  mark consumed
    # 11. release lock (finally)
```

### PathSafetyGuard.check_write_path()

```python
def check_write_path(self, path: str, role: str) -> Path:
    # normalize → reject ../ → reject absolute → reject drive escape
    # → follow symlink + recheck → check role-based allowlist
    # → return normalized Path or raise PathSafetyError
```

### ProposalValidator.validate()

```python
def validate(self, proposal: LedgerUpdateProposal, project_root: Path) -> ValidationResult:
    # check source_layer, source_artifact, evidence present
    # check source_artifact file exists
    # check operation matches target_ledger enum
    # classify errors: schema_repairable vs semantic_invalid
```

## 错误分类与 retry 策略

```python
class ErrorCategory(Enum):
    SCHEMA_REPAIRABLE = "schema_repairable"  # 缺字段、类型错、路径格式错 → retry 1-2 次
    SEMANTIC_INVALID = "semantic_invalid"    # evidence 指向不存在内容、claim 矛盾 → 不 retry，进 pause
```

## 边界条件处理

| 场景 | 处理 |
|---|---|
| arc_working_state 与 canon 冲突 | EmergencyPauseDetector → creative_review |
| foreshadowing 非法状态转换 | LedgerDiffGenerator → INVALID_FORESHADOW_TRANSITION |
| apply 中途 crash | rollback snapshot 恢复 |
| 同一 ledger_diff 重复 apply | ALREADY_CONSUMED |
| Agent 尝试写 canon | PathSafetyGuard 根据 role 拒绝 |
| proposal 缺 evidence 但格式正确 | schema_repairable → 可 retry |
| chapter review 有 blocking issues | 不合并 proposal，进 revision loop 或 pause |

## 测试策略

- **unit tests**：每个 validator/guard/system_script 独立测试
- **DoD tests**：`test_dod_1.py` ... `test_dod_10.py`，每个 DoD 一个文件
- **e2e tests**：`test_e2e_happy_path.py` + `test_e2e_failure_paths.py`
- **fixture 层级**：`tests/fixtures/toy_project/` 含完整目录结构 + 预置 JSON

## 技术栈

- Python 3.11+
- Pydantic v2（schema validation、JSON Schema 导出）
- pytest（测试、fixture）
- pathlib（路径操作、path safety）
- threading（进程内锁，MVP 单进程）
