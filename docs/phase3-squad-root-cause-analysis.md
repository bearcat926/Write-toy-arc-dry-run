# Phase 3 Squad 闲置根因分析报告

**日期**: 2026-06-02
**分析人**: Xiang (向明确), Product Director & Squad Lead
**范围**: Phase 3 全周期 — Squad 9 名 Agent 使用情况

---

## 摘要

Phase 3 期间共交付 20 个新模块、801 个测试，但 **10 名 Squad Agent 中 9 名零激活**，12+ 项目 skill 全未调用。以下为从设计文档到执行动作的完整根因追溯。

---

## 🔴 根因 1：Squad Lead 角色定义存在结构冲突

### 问题文件

> `pidan-fullstack-squad-lead.md` 第 36 行

```
Own the product from idea to impact. Translate ambiguous business problems
into clear, shippable plans... ensure every person on the team understands
what they're building...
```

### 冲突文件

> `pidan-fullstack-squad-lead.md` 第 20 行

```
As Squad Leader, you also own team orchestration: assigning work, unblocking
teammates, enforcing the SOP workflow...
```

### 分析

"Own from idea to impact" (第 36 行) 赋予 PM **端到端所有权**——从想法到交付，全程由 PM 负责。"Assigning work to teammates" (第 20 行) 则要求分派任务。两行之间存在**语义张力**：

| 行号 | 语义 | 自然解读 |
|------|------|---------|
| L36 | "Own from idea to impact" | 我来做 → **参与执行** |
| L20 | "assigning work, unblocking" | 分派给团队 → **协调执行** |

当两行同时生效时，端到端所有权因其更强的执行暗示而胜出。PM 被驱动向下亲自动手，而非向侧面协调。

### ⚠ 严重度：P0 — 角色定义层面的设计矛盾

---

## 🔴 根因 2：Vibe Coding 与 Squad 模式哲学互斥

### 问题文件

> `TEMP.md` 第 1-6 行

```
# Write-toy-arc-dry-run：Phase 3 扁平化 Vibe Coding 迭代计划
执行模式：Vibe Coding 驱动的扁平化产品迭代
```

> `TEMP.md` 第 44-53 行

```
为什么改用 Vibe Coding 模式：
小型团队会被会议、估算和任务拆分成本拖慢
需求意图 → 生成最小切片 → AI 辅助实现 → 本地运行 → 自动验证
```

> `TEMP.md` 第 184-202 行

```
扁平化执行模型：不设固定 Sprint，使用能力流
发现问题 → 建立能力卡片 → 定义最小可运行结果 → 生成或编写代码
```

### 冲突文件

> `pidan-fullstack-squad-lead.md` 第 504-552 行

```
SOP Workflow:
Stage Discovery → Stage Task Breakdown → Stage Validation → Stage Foundation
→ Stage Implementation Loop → Stage Release Gate → Stage Release
```

### 分析

TEMP.md 第 44 行明确说"小型团队会被会议、估算和任务拆分成本拖慢"——而 Squad SOP 的核心就是任务拆分和角色分工。两者直接矛盾：

| TEMP.md 主张 | Squad SOP 主张 | 结果 |
|-------------|---------------|------|
| 扁平化，单兵快跑 (L44) | 多角色流水线 (L504) | TEMP.md 胜出 |
| 不设固定 Sprint (L184) | Stage循环 + Release Gate (L533) | TEMP.md 胜出 |
| "AI 辅助实现" (L54) | "Backend + Frontend 实现" (L534) | TEMP.md 胜出 |

### ⚠ 严重度：P0 — 方法论层面的根本冲突

---

## 🟠 根因 3：SOP 管道未激活 — 无机会触发委派

### 问题文件

> `pidan-fullstack-squad-lead.md` 第 504-552 行

SOP 定义了 7 阶段流程：

```
Stage Discovery        (L508)  → ⬜ 跳过
Stage Task Breakdown   (L514)  → ⬜ 跳过
Stage Validation       (L521)  → ⬜ 跳过
Stage Foundation       (L527)  → ⬜ 跳过（Phase 2 已有基础设施）
Stage Implementation   (L533)  → ✅ 执行了，但是 PM 一人
Stage Release Gate     (L540)  → ⬜ 跳过
Stage Release          (L547)  → ⬜ 跳过
```

实际执行路径对照：

| SOP 阶段 | 定义 | 本阶段实际 |
|----------|------|-----------|
| Discovery | PM 运行访谈、分析 (L508) | ✅ TEMP.md 本身就是 Discovery 产出 |
| Task Breakdown | 写 PRD + ADR + 估算 (L514) | ⬜ TEMP.md Ready Queue 代替了正式 PRD/ADR |
| Validation | Prototyper 做 POC (L521) | ⬜ 跳过 — TEMP.md §17 定义「最小实现即验证」 |
| Foundation | 基础设施搭建 (L527) | ⬜ 跳过 — Phase 2 已完成 |
| Implementation | Backend + Frontend 实现 (L533) | ✅ 执行了 — **但是 PM 一人，非 Backend/Frontend** |
| Release Gate | Reality Checker 门禁 (L540) | ⬜ 跳过 — 测试通过即视为门禁通过 |
| Release | Git Master 发布 (L547) | ⬜ 跳过 — commit 留在本地（push 被沙箱阻断）|

**结论**: 7 阶段只执行了 1.5 个。没有 Task Breakdown 就没有委派任务卡 → Agent 没有工作可拿 → 全员闲置。

### ⚠ 严重度：P1 — 流程缺失导致委派机会不存在

---

## 🟠 根因 4：任务粒度低于委派经济阈值

### 问题文件

> `TEMP.md` 第 184-202 行

```
能力卡片状态：
Exploring → 尝试理解问题或验证假设
Building → 主动构建能力
Stable → 已通过测试 + 人工验证
```

> `TEMP.md` 第 54 行

```
生成最小切片 → AI 辅助实现 → 本地运行
```

### 分析

TEMP.md 定义的"最小切片"≈ 单个 Python 模块（200-500 行代码）。Agent 工具调用成本：

```
调用 Agent Tool
  → 写 300 字 prompt 描述任务      (~1 min)
  → 指定 subagent_type + team       (~30s)
  → Agent 加载上下文                (~10-30s)
  → Agent 执行                      (~5-15 min)
  → PM 审验收                      (~2 min)
  → 如果有问题：往返修复            (~5 min)
  
总计: ~15-25 min 协调成本
直接执行: Read + Write + Edit + Bash ≈ 20-30 min
```

当执行时间 ≈ 协调时间时，委派无经济优势。Phase 3 的 20 个模块均为 < 500 行的独立单元——每个都是"直接写更快"的尺度。

> 如果任务是"构建 100 章分布式处理管道"（3-5 天工作量），协调成本占比会从 50% 降到 5%，委派自然发生。

### ⚠ 严重度：P1 — 任务设计层面的结构性瓶颈

---

## 🟡 根因 5：TEMP.md 团队分工是扁平角色，非 Squad 角色

### 问题文件

> `TEMP.md` 第 1028-1045 行

```
18.1 推荐角色：
| Architecture Owner       | 守住安全边界，审核内核变更       |
| Backend Owner            | Store、Commit、Outbox、API、MCP  |
| AI / Retrieval Owner     | 检索、治理、Prompt、质量评估     |
| Frontend / Product Owner | 工作台、Dashboard、交付体验      |
| QA / Reliability Owner   | 自动化测试、压力测试、故障注入   |
| Domain Reviewer          | 小说创作规则、误报校准、用户体验 |

小团队允许一人兼任多个角色
```

### 冲突文件

> `pidan-fullstack-squad-lead.md` 第 490-500 行

```
Team Member Roster (9 人):
| backend-architect | Backend Architect | service implementation |
| frontend-developer | Frontend Engineer | UI implementation |
| ui-designer | Design Lead | visual design |
... etc
```

### 分析

TEMP.md 第 1028 行的"推荐角色"是 **6 个扁平 OWNER**——与 9 人 Squad 的角色映射是模糊的：

| TEMP.md Owner | Squad Agent | 映射清晰度 |
|--------------|-------------|-----------|
| Backend Owner | backend-architect | 清晰 |
| AI/Retrieval Owner | ❌ 无对应 | 缺失 |
| Frontend/Product Owner | frontend-developer + ui-designer | 部分 |
| QA/Reliability Owner | reality-checker | 部分 |
| Domain Reviewer | ❌ 无对应 | 缺失 |
| Architecture Owner | software-architect | 清晰 |

TEMP.md 说的"小团队允许一人兼任多个角色"（第 1037 行）进一步模糊了 Squad 的界限——它暗示一个 Owner 可以做多个人的事，这正好被 PM 解码为"我可以做所有人的事"。

### ⚠ 严重度：P2 — 角色映射空隙

---

## 🟡 根因 6：Squad Collaboration Rules 第 600 行未遵守

### 问题文件

> `pidan-fullstack-squad-lead.md` 第 578-600 行

```
Squad Collaboration Rules:
- **Backend Architect** owns backend implementation, APIs, databases, infrastructure
- **Frontend Developer** owns frontend implementation, accessibility, performance
... 
Do not override another role's authority without explicit delegation.
```

### 实际情况

PM 直接写了 bm25_retriever.py（Backend Architect 的职责域）、workbench.html（Frontend Developer 的职责域）、api.py（Backend Architect 的职责域）。第 600 行「Do not override」被实质违反。

### ⚠ 严重度：P1 — 规则已被违反

---

## 根因影响矩阵

| # | 类型 | 来源文件 | 行号 | 严重度 | 影响 |
|---|------|---------|------|--------|------|
| 1 | 角色语义冲突 | pidan-fullstack-squad-lead.md | L36 vs L20 | **P0** | PM 端到端所有权压倒委派 |
| 2 | 方法论冲突 | TEMP.md | L1-6, L44-53 | **P0** | Vibe Coding 单兵 vs Squad 团队 |
| 3 | SOP 未激活 | pidan-fullstack-squad-lead.md | L504-552 | **P1** | 无 Task Breakdown → 无委派 |
| 4 | 委派经济性 | TEMP.md | L54, L184-202 | **P1** | 30min 模块不值得委派 |
| 5 | 角色映射空隙 | TEMP.md | L1028-1037 | **P2** | 6 Owner 模糊对应 9 Agent |
| 6 | 规则违反 | pidan-fullstack-squad-lead.md | L578-600 | **P1** | PM 亲手写代码，越过 Backend/Frontend |

---

## 修正建议

| 根因 | 短修 | 长修 |
|------|------|------|
| 1 (L36冲突) | 在 Squad Lead 提示中增加触发条件：当任务量 > 500行时，必须委派 | 将 L36 的 "own from idea to impact" 改为 "own the outcomes, delegate the execution" |
| 2 (TEMP方法) | Phase 4 计划明确区分 Vibe Coding 区域 vs Squad 区域 | TEMP.md 增加 Squad 模式声明段 |
| 3 (SOP跳过) | 100章跑完后立即激活 Stage 6 Release Gate (Reality Checker) | 下一个完整迭代按 SOP 全程走流 |
| 4 (委派经济) | Phase 4 任务按子系统而非模块组织 | 每个子系统 > 3天工作量 |
| 5 (角色映射) | TEMP.md 增加明确 Squad Agent 映射表 | 合并两套角色列为统一 RACI 矩阵 |
| 6 (规则违反) | 立即委派 Code Reviewer 审查 Phase 3 代码 | 新代码严格遵守第 578 行角色边界 |
