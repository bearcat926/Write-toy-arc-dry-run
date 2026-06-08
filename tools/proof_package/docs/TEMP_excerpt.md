| ID   | 任务项              | 描述                                     | 依赖       | 交付物       | 快速验证点              |
| ---- | ------------------- | ---------------------------------------- | ---------- | ------------ | ----------------------- |
| I-01 | 建立 20 章夹具      | 用于快速回归                             | A-03       | Fixture      | 每次提交可运行          |
| I-02 | 建立 100 章夹具     | 用于长篇验证                             | I-01       | Fixture      | 可批量生成              |
| I-03 | 连续提交测试        | 持续处理章节提交                         | C-05、I-02 | Test Report  | 无不可恢复错误          |
------

# 24. Phase 3 正式完成条件

Phase 3 完成不是“所有任务都做完”，而是以下主路径全部晋升：

```text
安全内核保护层 Promoted
+
DerivedArtifactStore Promoted
+
ChapterCommit Promoted
+
BM25 与 Retrieval Trace Promoted
+
Governance Shadow Promoted
+
hard_pause 可选启用
+
Outbox Promoted
+
MCP 只读或 propose-only Promoted
+
作者工作台闭环 Promoted
+
100 章验证通过
```

允许仍处于实验状态：

```text
Vector Adapter
Reranker
Style Lab
Genre Profile
高级可视化
插件市场
复杂图数据库
```
