# Comet Design Handoff

- Change: toy-arc-dry-run
- Phase: design
- Mode: compact
- Context hash: 0f9d4abbf277dd0b2c9b21397ec95c1a7ec0ab463a9cf8140dee2d9ba95045b6

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/toy-arc-dry-run/proposal.md

- Source: openspec/changes/toy-arc-dry-run/proposal.md
- Lines: 1-32
- SHA256: 08c2d07b4efb942091caa717b94b39936f4a56bfc5e2adfa71cd96dad8b2fd41

```md
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
```

## openspec/changes/toy-arc-dry-run/design.md

- Source: openspec/changes/toy-arc-dry-run/design.md
- Lines: 1-105
- SHA256: 13e2f137e79ffda6eaa9ff64629e838830612e3c8a09945d0ac6971095434c72

[TRUNCATED]

```md
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

```

Full source: openspec/changes/toy-arc-dry-run/design.md

## openspec/changes/toy-arc-dry-run/tasks.md

- Source: openspec/changes/toy-arc-dry-run/tasks.md
- Lines: 1-52
- SHA256: 5938cc98056d56efe4b3b0248bb9085b8a420f7c2e791a423f446b4fe91bc6f0

```md
## 1. 项目骨架

- [ ] 1.1 初始化 Python 项目：pyproject.toml、src/novel_workflow/ 包结构、tests/ 目录
- [ ] 1.2 创建 Pydantic config 模块：支持的 schema_version 列表、allowlist 路径定义、retry policy、pause taxonomy enum
- [ ] 1.3 实现 toy_project 目录初始化脚本（按 PLAN.md Section 11 文件协议创建全部目录和空文件）

## 2. Schema 定义

- [ ] 2.1 定义 Pydantic models：GateRecord、LedgerUpdateProposal（含 operation enum per target_ledger）、LedgerDiff、CanonDiff、ArcWorkingStateEntry（含 status、depends_on）、PauseReport（含 pause_type enum）、ProgressEntry、ApplyRecord
- [ ] 2.2 定义 3 个 ledger 的 Pydantic models：TimelineEvent、CharacterKnowledgeEntry、ForeshadowEntry（含状态机：introduced → developed → paid_off / abandoned）
- [ ] 2.3 定义 chapter_effect_report Pydantic model（scene_goal、state_changes、character_choices、conflict_or_pressure_change、new_reader_questions）

## 3. Guards

- [ ] 3.1 实现 PathSafetyGuard：normalize、allowlist 检查、../ 拒绝、绝对路径拒绝、Windows drive escape 拒绝、symlink escape 拒绝
- [ ] 3.2 实现 LockManager：进程内 threading.Lock、单任务模式、finally 释放语义、lock timeout 报错

## 4. Validators

- [ ] 4.1 实现 SchemaValidator：检查 schema_version 存在性和支持性
- [ ] 4.2 实现 GateRecordValidator：author_input_evidence 非空检查、approval_level 字段检查（lightweight / strict）
- [ ] 4.3 实现 ProposalValidator：source_layer / source_artifact / evidence 必填、source_artifact 文件存在性检查、operation enum 与 target_ledger 匹配检查、error 分类（schema_repairable vs semantic_invalid）

## 5. 系统脚本

- [ ] 5.1 实现 ArcWorkingStateManager：从 canon/ledgers 初始化、valid proposal merge、status 标记、depends_on 依赖级联失效
- [ ] 5.2 实现 LedgerDiffGenerator：从 merged proposals 生成 ledger_diff.json，按 ledger 类型应用不同 merge 策略（timeline append-only、character_knowledge append-only、foreshadowing 状态机）
- [ ] 5.3 实现 Canonicalizer：将 approved drafts 复制到 canon/manuscript/
- [ ] 5.4 实现 AtomicApplyManager：validate gate → validate schema → lock → validate not consumed → snapshot → canonicalize → apply ledger_diff → apply canon_diff → write apply_record → mark consumed → release lock（finally）
- [ ] 5.5 实现 EmergencyPauseDetector：根据触发条件分类 hard_pause / creative_review / soft_warning、写 pause_report.jsonl

## 6. Fixture 数据

- [ ] 6.1 创建 fixture：direction_gate.json（approved）、arc_contract.md（含 hard requirement 和 absolute prohibition）、arc_start_gate.json（approved）
- [ ] 6.2 创建 fixture：ch_001/ch_002/ch_003 的 draft.md、review.json、ledger_update_proposal.json（含有效 source/evidence）
- [ ] 6.3 创建 fixture：arc_end_gate.json（approved）、invalid_proposal（缺 evidence）、path_traversal_proposal、duplicate_apply 场景

## 7. 测试

- [ ] 7.1 测试 DoD #1：Agent 禁写 canon/ledgers/arc_working_state/ledger_diff/gate
- [ ] 7.2 测试 DoD #2：gate record 缺 evidence 拒绝、auto-generated evidence 拒绝
- [ ] 7.3 测试 DoD #3：proposal 不能直接 apply
- [ ] 7.4 测试 DoD #5：checkpoint / progress.jsonl 注入叙事字段失败
- [ ] 7.5 测试 DoD #7：atomic apply 全成功、中途失败回滚、重复 apply 拒绝
- [ ] 7.6 测试 DoD #8：missing / unknown schema_version 拒绝
- [ ] 7.7 测试 DoD #10：path traversal、绝对路径、symlink escape 拒绝

## 8. 端到端验收

- [ ] 8.1 实现 happy path 端到端测试：init → direction gate → arc_start gate → 3 chapters (draft/review/proposal/merge) → arc_end gate → atomic apply → verify canon/manuscript + ledgers updated
- [ ] 8.2 实现 failure path 测试：proposal schema invalid、evidence 缺失、gate evidence 缺失、plugin 越权、path traversal、apply 中途失败、duplicate apply、unknown schema version
- [ ] 8.3 验证 progress.jsonl 包含全部关键事件、pause taxonomy 正确分类、chapter_effect_report 生成
```

## openspec/changes/toy-arc-dry-run/specs/arc-state-management/spec.md

- Source: openspec/changes/toy-arc-dry-run/specs/arc-state-management/spec.md
- Lines: 1-41
- SHA256: 86ea0e505f69dff3bbaea5b5f87cb67f6c0be8159581d11b72f247cca51c5c5b

```md
## ADDED Requirements

### Requirement: arc_working_state initialized from canon and ledgers
The system SHALL initialize `arc_working_state.json` from current canon and ledger state when an arc starts.

#### Scenario: Fresh arc initialization
- **WHEN** arc_start gate is approved
- **THEN** `arc_working_state.json` is created with current canon facts and ledger snapshots, all entries having `status: "working_accepted"`

### Requirement: Valid proposals merged into arc_working_state by system script
The system SHALL merge validated proposals into `arc_working_state` after chapter review passes and proposal validation succeeds.

#### Scenario: Successful merge
- **WHEN** ch_001 passes review and its proposal validates
- **THEN** proposal entries are added to `arc_working_state` with `status: "working_accepted"`, `source_chapter: "ch_001"`, and `approval_scope: "arc_internal_only"`

#### Scenario: Audit failure blocks merge
- **WHEN** ch_001 review reports blocking issues but proposal validates
- **THEN** proposal is NOT merged into `arc_working_state`

### Requirement: arc_working_state acts as overlay, not override
The system SHALL treat `arc_working_state` as having higher recency but NOT higher authority than canon/ledgers.

#### Scenario: Overlay with conflict detection
- **WHEN** `arc_working_state` has `character_A knows secret_X` but canon says `character_A does not know secret_X`
- **THEN** system detects the conflict and triggers `creative_review` pause

#### Scenario: Overlay without conflict
- **WHEN** `arc_working_state` has a new fact `character_B arrived at location_Y` that does not contradict canon
- **THEN** the new fact is available as arc overlay for subsequent chapters

### Requirement: Rejected arc_working_state entries trigger dependency cascade
The system SHALL propagate rejection to downstream entries that depend on rejected entries.

#### Scenario: Cascade rejection
- **WHEN** `aws_001` (from ch_001) is marked `rejected` and `aws_002` (from ch_002) has `depends_on: ["aws_001"]`
- **THEN** `aws_002` is marked `invalidated_by_rejected_dependency`

#### Scenario: Independent entries survive
- **WHEN** `aws_001` is rejected but `aws_003` has no `depends_on` referencing `aws_001`
- **THEN** `aws_003` retains its current status
```

## openspec/changes/toy-arc-dry-run/specs/control-plane/spec.md

- Source: openspec/changes/toy-arc-dry-run/specs/control-plane/spec.md
- Lines: 1-76
- SHA256: e586a80557448d1fc207a764d0cd2648700abda3d7b5a9a12ca1562133c2dabe

```md
## ADDED Requirements

### Requirement: Schema validator rejects unknown or missing schema_version
The system SHALL reject any persistent JSON or Markdown frontmatter that lacks `schema_version` or has an unknown version.

#### Scenario: Missing schema_version
- **WHEN** a JSON artifact is submitted without `schema_version` field
- **THEN** validator returns error `MISSING_SCHEMA_VERSION` and the artifact is rejected

#### Scenario: Unknown schema_version
- **WHEN** a JSON artifact has `schema_version: "99.0"` which is not in the supported version list
- **THEN** validator returns error `UNKNOWN_SCHEMA_VERSION` and the artifact is rejected

#### Scenario: Valid schema_version
- **WHEN** a JSON artifact has `schema_version: "1.0"` which is in the supported version list
- **THEN** validator passes and continues to field-level validation

### Requirement: Gate record validator enforces author_input_evidence
The system SHALL reject any approved gate record that lacks `author_input_evidence` or has empty/whitespace-only evidence.

#### Scenario: Approved gate with empty evidence
- **WHEN** a gate record has `decision: "approved"` and `author_input_evidence: ""`
- **THEN** validator returns error `MISSING_GATE_EVIDENCE`

#### Scenario: Approved gate with auto-generated evidence
- **WHEN** a gate record has `decision: "approved"` and `author_input_evidence` matching the pattern `"auto_*"`
- **THEN** validator returns error `AUTO_GENERATED_GATE_EVIDENCE`

#### Scenario: Approved gate with valid evidence
- **WHEN** a gate record has `decision: "approved"` and `author_input_evidence: "Arc direction aligns with story goals"`
- **THEN** validator passes

#### Scenario: Rejected gate without evidence
- **WHEN** a gate record has `decision: "rejected"` and `author_input_evidence` is empty
- **THEN** validator passes (evidence not required for rejection)

### Requirement: Proposal validator enforces source citation
The system SHALL reject any `ledger_update_proposal` that lacks `source_layer`, `source_artifact`, or `evidence`.

#### Scenario: Proposal missing evidence
- **WHEN** a proposal has `source_layer` and `source_artifact` but no `evidence`
- **THEN** validator returns error `MISSING_EVIDENCE` with error category `schema_repairable`

#### Scenario: Proposal with evidence pointing to nonexistent artifact
- **WHEN** a proposal has `source_artifact: "arcs/arc_001/drafts/ch_999.md"` but that file does not exist
- **THEN** validator returns error `INVALID_SOURCE_ARTIFACT` with error category `semantic_invalid`

#### Scenario: Valid proposal
- **WHEN** a proposal has all required fields and `source_artifact` points to an existing file
- **THEN** validator passes

### Requirement: Proposal validator enforces operation enum per target_ledger
The system SHALL validate that `operation` field matches the allowed operations for the specified `target_ledger`.

#### Scenario: timeline with invalid operation
- **WHEN** a proposal has `target_ledger: "timeline"` and `operation: "delete_event"`
- **THEN** validator returns error `INVALID_OPERATION` (timeline only allows `append_event | correction`)

#### Scenario: foreshadowing with valid operation
- **WHEN** a proposal has `target_ledger: "foreshadowing"` and `operation: "introduce_foreshadow"`
- **THEN** operation validation passes

### Requirement: Emergency pause detector classifies pause type
The system SHALL classify each pause into `hard_pause`, `creative_review`, or `soft_warning`.

#### Scenario: Path traversal triggers hard_pause
- **WHEN** path safety guard detects `../` in a write path
- **THEN** pause type is `hard_pause`

#### Scenario: POV knowledge violation triggers creative_review
- **WHEN** a proposal suggests a character knows information outside their POV boundary
- **THEN** pause type is `creative_review`

#### Scenario: Weak hook triggers soft_warning
- **WHEN** reviewer reports no reader hook in a chapter
- **THEN** pause type is `soft_warning`
```

## openspec/changes/toy-arc-dry-run/specs/dry-run-fixtures/spec.md

- Source: openspec/changes/toy-arc-dry-run/specs/dry-run-fixtures/spec.md
- Lines: 1-38
- SHA256: e597664961bb11a98eb4bc4aa88d64e3168d276460c782b082923aae5eff1f4b

```md
## ADDED Requirements

### Requirement: Fixture-based end-to-end test covers all DoD scenarios
The system SHALL provide pytest fixtures that simulate a 3-chapter toy arc and verify all 10 DoD items.

#### Scenario: Happy path end-to-end
- **WHEN** fixture initializes a toy project, creates direction gate, arc_start gate, 3 chapters with draft/review/proposal, arc_end gate, and atomic apply
- **THEN** all steps complete without error and canon/manuscript + ledgers are updated correctly

#### Scenario: DoD #1 - Agent write rejection
- **WHEN** fixture attempts to write to `canon/` using an Agent role
- **THEN** write is rejected with error `AGENT_WRITE_DENIED`

#### Scenario: DoD #2 - Gate evidence enforcement
- **WHEN** fixture creates a gate record with `decision: "approved"` and empty `author_input_evidence`
- **THEN** gate validator rejects it

#### Scenario: DoD #7 - Atomic apply rollback
- **WHEN** fixture triggers a failure mid-apply (between canonicalize and ledger_diff)
- **THEN** all pre-apply state is restored

#### Scenario: DoD #10 - Path traversal rejection
- **WHEN** fixture submits a write path with `../`
- **THEN** path safety guard rejects it

### Requirement: Dry run produces observable artifacts
The system SHALL generate all expected artifacts during dry run: gate records, drafts, reviews, proposals, arc_working_state, ledger_diff, canon_diff, apply_record, pause_report, progress.jsonl.

#### Scenario: All artifacts exist after dry run
- **WHEN** complete 3-chapter dry run finishes
- **THEN** all expected files exist in the toy_project directory with valid schema_version

### Requirement: progress.jsonl records all system events
The system SHALL log every significant system event to `workspace/progress.jsonl` with schema_version and `contains_narrative_fact: false`.

#### Scenario: Event logging
- **WHEN** a proposal is validated
- **THEN** a progress entry is written with `event_type`, `timestamp`, `artifact_path`, and `contains_narrative_fact: false`
```

## openspec/changes/toy-arc-dry-run/specs/file-protocol/spec.md

- Source: openspec/changes/toy-arc-dry-run/specs/file-protocol/spec.md
- Lines: 1-46
- SHA256: e78c31ce9f24f96fc2fdae2ebeffbeec39b57dd58aae5ba6e5d1d2fa3ac4e4b9

```md
## ADDED Requirements

### Requirement: Path safety guard normalizes and validates all write paths
The system SHALL normalize every write path and validate against an allowlist before any file operation.

#### Scenario: Path traversal rejected
- **WHEN** a write path contains `../`
- **THEN** guard returns error `PATH_TRAVERSAL_REJECTED`

#### Scenario: Absolute path rejected
- **WHEN** a write path starts with `/` or `C:\`
- **THEN** guard returns error `ABSOLUTE_PATH_REJECTED`

#### Scenario: Symlink escape rejected
- **WHEN** a write path resolves via symlink to a location outside the workspace allowlist
- **THEN** guard returns error `SYMLINK_ESCAPE_REJECTED`

#### Scenario: Valid path passes
- **WHEN** a write path is `arcs/arc_001/drafts/ch_001.md` and that directory exists in the allowlist
- **THEN** guard passes and returns the normalized path

### Requirement: File protocol defines canonical project structure
The system SHALL enforce the project directory structure as defined in PLAN.md Section 11.

#### Scenario: canon/manuscript directory exists
- **WHEN** a project is initialized
- **THEN** `canon/manuscript/` directory is created for approved chapter text

#### Scenario: gates directory at project root
- **WHEN** a project is initialized
- **THEN** `gates/direction_gate.json` exists as a project-level gate (not arc-level)

#### Scenario: reports directory contains canon_diff.json location
- **WHEN** an arc is initialized
- **THEN** `arcs/arc_XXX/reports/` directory is created with space for `canon_diff.json`

### Requirement: Plugin write paths default deny
The system SHALL reject any plugin write request to paths not in the explicit plugin allowlist.

#### Scenario: Plugin attempts to write canon
- **WHEN** a plugin requests write to `canon/canon_state.json`
- **THEN** guard returns error `PLUGIN_WRITE_DENIED`

#### Scenario: Plugin writes to allowed path
- **WHEN** a plugin requests write to `inspiration/idea_001.md`
- **THEN** guard passes
```

## openspec/changes/toy-arc-dry-run/specs/ledger-system/spec.md

- Source: openspec/changes/toy-arc-dry-run/specs/ledger-system/spec.md
- Lines: 1-41
- SHA256: 5cb6268959a50b9b67b83df53c8cdc049984ce6eddc5d456a141f123f3696a5e

```md
## ADDED Requirements

### Requirement: Ledger diff generator produces valid diff from merged proposals
The system SHALL generate a `ledger_diff.json` from validated proposals merged during an arc, with per-ledger merge strategies.

#### Scenario: Timeline append-only
- **WHEN** 3 chapters produce timeline proposals with `operation: "append_event"`
- **THEN** ledger_diff contains 3 appended events in order, no deletions or modifications

#### Scenario: Foreshadowing state machine
- **WHEN** ch_001 introduces a foreshadow and ch_003 pays it off
- **THEN** ledger_diff contains `introduce_foreshadow` followed by `pay_off_foreshadow` with valid state transitions

#### Scenario: Foreshadowing invalid transition rejected
- **WHEN** a proposal attempts `paid_off → introduced`
- **THEN** diff generator returns error `INVALID_FORESHADOW_TRANSITION`

### Requirement: Canonicalizer moves draft to canon/manuscript
The system SHALL move approved draft content from `arcs/arc_XXX/drafts/ch_YYY.md` to `canon/manuscript/ch_YYY.md` during atomic apply.

#### Scenario: Successful canonicalization
- **WHEN** arc_end gate is approved and atomic apply runs
- **THEN** `ch_001.md`, `ch_002.md`, `ch_003.md` appear in `canon/manuscript/` and drafts remain in arc directory

### Requirement: Atomic apply is all-or-nothing
The system SHALL apply canonicalize draft + ledger_diff + canon_diff as a single atomic operation.

#### Scenario: All succeed
- **WHEN** canonicalize, ledger_diff apply, and canon_diff apply all succeed
- **THEN** all changes are persisted and apply_record is written

#### Scenario: Partial failure triggers rollback
- **WHEN** canonicalize succeeds but ledger_diff apply fails
- **THEN** all changes are rolled back to pre-apply state using snapshot

### Requirement: Consumed ledger_diff cannot be reapplied
The system SHALL mark applied ledger_diff as consumed and reject duplicate apply attempts.

#### Scenario: Duplicate apply rejected
- **WHEN** the same `ledger_diff.json` (same target_artifact + same diff hash) is submitted for apply a second time
- **THEN** apply manager returns error `ALREADY_CONSUMED`
```

