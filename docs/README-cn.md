# 文档

本文档目录按逻辑类别组织。请参考以下章节查找所需内容。

---

## 项目定义与分析

- **[PRD](synthesis/prd.md)** — 原始产品需求文档
- **[项目简报](synthesis/PROJECT_BRIEF.md)** — 当前范围、决策和约束
- **[项目详情](synthesis/PROJECT_DETAILS.md)** — 深度分析、源码地图、风险评估
- **[演进中的论点](synthesis/EVOLVING_THESIS.md)** — 持续更新的跨源综合、开放问题和决策
- **[已知差距](known-gaps.md)** — 缺失能力和改进建议

## 架构

- **[架构决策记录](adr/)** — 以 Context / Decision / Consequences 格式记录的关键决策
  - `001` — 双 LLM 架构
  - `002` — SQLite FTS5 而非 Postgres
  - `003` — SSE 流式传输模式
  - `004` — 文档管理规范化

## 规格与计划

- **[设计规格](specs/)** — 每个功能的详细设计文档
  - FastAPI 骨架、类型化模型与配置、聊天前端、MCP 服务器、UI 重新设计、Wiki 图谱视图、双层 LLM、手动保存到记忆
- **[实施计划](plans/)** — 每个规格的可执行实施计划

## 指南与方法论

- **[收集 → 蒸馏 → 摄入](guides/collect-distill-ingest.md)** — 多 LLM 知识蒸馏方法论
- **[项目管理](guides/project-management.md)** — GitHub 工作流、ADR 流程、变更日志约定

## 主题总结

- **[聊天 + 记忆工作流](topics/chat-memory-workflow.md)** — 核心双速聊天/记忆循环
- **[摄入 + 检索管线](topics/ingest-retrieval-pipeline.md)** — 管线端到端工作方式
- **[文档管理](topics/document-management.md)** — 文档的组织和维护方式

## 研究资料（只读）

多 LLM 研究输出，为设计提供参考。作为不可变证据保留。

- **[v1 — 第一轮](research/v1/)** — Claude、ChatGPT、Gemini 原始响应
- **[v2 — 第二轮](research/v2/)** — 修订版计划，更注重实施
- **[v3 — 第三轮](research/v3/)** — DeepSeek、OpenCode、Copilot 分析与路线图

## 参考资料

- **[参考文献](references/)** — 架构图、设计灵感和背景分析

## 外部链接

- [变更日志](../CHANGELOG.md) — 版本发布历史
- [路线图](roadmap.md) — 里程碑级计划
