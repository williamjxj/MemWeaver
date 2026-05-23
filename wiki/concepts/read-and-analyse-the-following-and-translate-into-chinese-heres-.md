---
id: read-and-analyse-the-following-and-translate-into-chinese-heres-
title: "read and analyse the following, and translate into chinese: Here's the full expe…"
type: concept
tags: ["ml"]
confidence: medium
created: 2026-05-23
updated: 2026-05-23
sources: ["ing_20260523_a736baf8"]
---

## Summary

这里是完整的专家分析： --- **① MemWeaver — MCP 与提示词框架 (Prompt Harness)** 你的提示词框架已经相当稳固（已具备 `.cursorrules`、`CLAUDE.md`、`AGENTS.md`）。真正的差距在于：**加入 MCP 服务器**。 你的 `/query`、`/ingest` 和 `/chat` FastAPI 端点可以完美映射到 MCP 工具。一旦这些接口被暴露，Cursor 或 Claude Code 就能在编码会话中直接调用你的 Wiki 搜索功能——这使得 MemWeaver 不再仅仅是一个独立应用，而是成为 IDE 的实时记忆层。 使用 `mcp-server` Python 库或 FastAPI MCP 扩展即可实现，这仅仅是对你已有功能的轻量级封装。 --- **② 多 LLM → 编码工具** **工作流程：** 向 C…

## Key claims

- (none)
