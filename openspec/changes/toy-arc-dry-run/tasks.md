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
