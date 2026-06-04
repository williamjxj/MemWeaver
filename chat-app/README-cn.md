# mem-weaver 聊天应用

**MemWeaver** 双模型记忆系统的聊天前端。将问题发送至 FastAPI 后端，通过 SSE 流式接收响应，以富文本 Markdown 渲染输出，并展示 Wiki 记忆上下文。提供 5 标签仪表盘，可探索完整管线。

## 仪表盘

| 比较（三阶段并排） | QA 聊天（DeepSeek 流式） |
|---|---|
| ![比较视图](../assets/memweaver-compare.png) | ![QA 聊天视图](../assets/memweaver-qa-chat.png) |

| RAG（混合检索） | LLM-Wiki（蒸馏记忆） |
|---|---|
| ![RAG 视图](../assets/memweaver-rag.png) | ![LLM-Wiki 视图](../assets/memweaver-llm-wiki.png) |

| 库存（记录计数 + Wiki 图谱） |
|---|
| ![库存视图](../assets/memweaver-inventory.png) |

## 功能特性

- **5 标签仪表盘** — 在比较、QA 聊天、RAG、LLM-Wiki 和库存视图间切换
- **SSE 流式输出** — Token 逐个到达，通过 DeepSeek 增量渲染
- **Markdown 输出** — 助手响应使用 `react-markdown`（GFM：表格、列表、代码块、链接）渲染
- **Wiki 侧边栏** — 每次聊天后，相关 Wiki 文章显示在侧面板
- **RAG + LLM-Wiki 面板** — 查询混合 BM25/sqlite-vec 检索层，或关键词搜索蒸馏后的 Wiki
- **库存面板** — 浏览原始 QA、Wiki 概念、数据库表、索引和日志中的记录计数，并配有交互式力导向 Wiki 图谱
- **手动保存到记忆** — 仅在你选择时将问答保存到 Wiki（可附加备注）

## 技术栈

- **Next.js 16**（App Router）
- **Tailwind CSS 4** + shadcn/ui
- **react-markdown** + **remark-gfm** 用于富文本渲染
- **TypeScript**

## 快速开始

确保先运行 FastAPI 后端（从仓库根目录）：

```bash
uvicorn server.main:app --reload
```

然后启动前端：

```bash
pnpm install
pnpm dev
```

在浏览器中打开 [http://localhost:3000](http://localhost:3000)，使用标签栏探索每个视图。

## 生产构建

```bash
pnpm build
```
