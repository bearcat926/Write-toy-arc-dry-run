# 内核保护边界清单 (Kernel Boundary)

**Phase 3 — A-01 | 版本：1.0 | 状态：Verified**
**目的**：明确系统的正式写入入口和禁止路径，确保任何代码（UI、Agent、Plugin、Worker）都不得绕过安全边界。

---

## 1. 核心不变量

```
Agent / UI / Plugin
       ↓
Proposal 或受控查询接口
       ↓
Validator
       ↓
Human Gate
       ↓
Atomic Apply
       ↓
Canon + Ledgers
```

## 2. 正式写入入口 (唯一合法路径)

| 入口 | 模块 | 类/函数 | 角色 | 说明 |
|------|------|---------|------|------|
| **Proposal 验证** | `validators/proposal_validator.py` | `ProposalValidator.validate()` | system_script | 唯一进入提议链的入口 |
| **Gate 验证** | `validators/gate_validator.py` | `GateValidator.validate()` | system_script | 唯一进入审批链的入口 |
| **Atomic Apply** | `system_scripts/atomic_apply_manager.py` | `AtomicApplyManager.apply()` | system_script | 唯一正式写入 canon + ledger 的入口 |
| **Ledger Diff 生成** | `system_scripts/ledger_diff_generator.py` | `LedgerDiffGenerator.generate()` | system_script | 生成 ledger diff |
| **Canonicalizer** | `system_scripts/canonicalizer.py` | `Canonicalizer.canonicalize()` | system_script | 将 draft 拷贝至 canon/manuscript |
| **Snapshot Rollback** | `system_scripts/atomic_apply_manager.py` | `AtomicApplyManager.apply()` (内部) | system_script | apply 失败时自动回滚 |

## 3. 受保护目录 (禁止直接写入)

| 目录 | 保护方式 | 强制者 |
|------|----------|---------|
| `canon/manuscript/` | 仅 AtomicApplyManager 可写 | PathSafetyGuard (canon_manuscript) |
| `canon/characters/` | 仅 AtomicApplyManager 可写 | PathSafetyGuard (canon_characters) |
| `ledgers/*.json` | 仅 AtomicApplyManager 可写 | PathSafetyGuard (ledgers) |
| `workspace/consumed_hashes.json` | 仅 AtomicApplyManager 可写 | PathSafetyGuard (consumed_hashes) |
| `workspace/phase2/manifest.json` | 仅 ManifestManager 原子写入 | ManifestManager |

## 4. 守卫机制

| 守卫 | 模块 | 作用 |
|------|------|------|
| **PathSafetyGuard** | `guards/path_safety.py` | 角色白名单；拒绝路径遍历、绝对路径、符号链接逃逸 |
| **LockManager** | `guards/lock_manager.py` | 单进程内存锁，防止并发 apply |
| **DerivedArtifactPolicy** | `validators/derived_artifact_policy.py` | 禁止派生工件进入事实链 |
| **SourceArtifactPolicy** | `validators/source_artifact_policy.py` | 来源工件 denylist + layer 验证 |
| **SchemaValidator** | `validators/schema_validator.py` | 入站数据 schema 版本检查 |
| **ReplayContract** | `system_scripts/replay_contract.py` | 确定性重放输入快照 |
| **StableGenerationPointer** | `system_scripts/stable_generation_pointer.py` | 只读稳定代际指针 |
| **consumed_hashes** | `system_scripts/atomic_apply_manager.py` | 拒绝重复 apply (幂等) |

## 5. 禁止路径 (必须由 CI 阻断)

以下写入行为属于**安全违规**，CI 必须失败：

### 5.1 Agent 写入 canon/ledgers
```python
# 禁止
agent → canon/manuscript/*.md
agent → canon/characters/*.json
agent → ledgers/*.json
```
**检测方式**：扫描 `crewai/tools.py` 及其他 Agent 相关代码中的 `write`/`open(w)` 调用，检查目标路径是否在 cannon/ledgers 下。

### 5.2 UI 直接写存储
```python
# 禁止
UI → 直接访问 canon/、ledgers/、workspace/consumed_hashes.json
UI → 直接修改 manifest.json
```
**检测方式**：如果未来增加 UI 层，扫描 UI 代码中对 `canon/`、`ledgers/` 路径的直接引用。

### 5.3 Worker 绕过 apply
```python
# 禁止
Async Worker → canon/*.json
Async Worker → ledgers/*.json
Worker → 自动晋升 stable generation（必须通过 human gate）
```
**检测方式**：扫描所有 async/worker 代码中的文件写入操作。

### 5.4 Plugin 突破沙盒
```python
# 禁止
Plugin → canon/、ledgers/、manifest.json
```
**检测方式**：Plugin 只允许写 `inspiration/`、`prompts/`、`variants/`、`profiles/`、`asset_index/` 等目录。

### 5.5 派生工件作为事实源
```python
# 禁止
workspace/summaries/* → 作为 proposal 的唯一证据源
workspace/reports/* → 替代 canon 作为事实源
```
**检测方式**：`derive_artifact_policy.is_derived_artifact()` 已在 atomic_apply 的 `_prevalidate_ledger_diff()` 中使用。

### 5.6 LLM 输出自动晋升
```python
# 禁止
LLM 输出 → 不经过 human gate → canon
LLM 输出 → 不经过 proposal → ledger
```
**强制者**：`GateValidator` 拒绝 synthetic gate（非 dry-run 模式）和自动生成的 evidence。

## 6. 角色写入权限矩阵

| 路径 | Agent | system_script | plugin | UI |
|------|-------|---------------|--------|----|
| `arcs/*/drafts/` | ✅ | ❌ | ❌ | ❌ |
| `arcs/*/reviews/` | ✅ | ❌ | ❌ | ❌ |
| `arcs/*/proposals/` | ✅ | ❌ | ❌ | ❌ |
| `arcs/*/variants/` | ✅ | ❌ | ❌ | ❌ |
| `arcs/*/reports/` | ❌ | ✅ | ❌ | ❌ |
| `arcs/*/archive/` | ❌ | ✅ (snapshots) | ❌ | ❌ |
| `canon/manuscript/` | ❌ | ✅ (仅 apply) | ❌ | ❌ |
| `canon/characters/` | ❌ | ✅ (仅 apply) | ❌ | ❌ |
| `ledgers/` | ❌ | ✅ (仅 apply) | ❌ | ❌ |
| `workspace/` (派生) | ❌ | ✅ | ❌ | ❌ |
| `inspiration/` | ❌ | ❌ | ✅ | ❌ |
| `prompts/` | ❌ | ❌ | ✅ | ❌ |

## 7. 回滚与恢复入口

| 入口 | 模块 | 说明 |
|------|------|------|
| **apply 内回滚** | `AtomicApplyManager.apply()` | snapshot → 异常 → 恢复 |
| **Stable pointer rollback** | `StableGenerationPointer.rollback_to_previous()` | 标记当前 stable 为 stale |
| **Rebuild** | `RebuildOrchestrator` | 从 canon + ledgers 重建所有派生制品 |
| **Replay 验证** | `ReplayContract.validate_replay()` | 验证重放输入一致性 |

## 8. 检查清单 (每次提交前)

- [ ] 是否新增了写入 canon/ledgers 的路径？
- [ ] 是否所有写入入口都经过 PathSafetyGuard？
- [ ] 是否所有 proposal 来源都经过 `is_derived_artifact()` 检查？
- [ ] 是否所有 gate evidence 都经过 GateValidator？
- [ ] 是否 apply 前都检查了 consumed_hashes？
- [ ] 是否新增了绕过 proposal/gate/apply 的直接写入？
- [ ] 是否在非 apply 上下文中写了 ledgers/ 或 canon/？
- [ ] 是否所有派生制品都标记为 `derived=True`？

## 9. 向后兼容性

本文档覆盖以下现有模块的全部安全边界：
- `AtomicApplyManager` (apply + rollback)
- `GateValidator` / `ProposalValidator`
- `PathSafetyGuard` (三级角色白名单)
- `DerivedArtifactPolicy`
- `StableGenerationPointer`
- `ReplayContract`
- `ManifestManager`
- `RebuildOrchestrator`
- `consumed_hashes` 幂等机制

**如果后续增加新模块需要扩展内核边界，必须同时更新本文档。**
