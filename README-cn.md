# LLM-Wiki Middleware Delegator — MemWeaver

📖 [English](README.md) · [中文](README-cn.md)

FastAPI 后端 + Next.js 16 聊天前端 + stdio MCP 服务器，实现了一套**双模型内存管线**（参见 [`docs/research/v2/s2-claude-plan.md`](docs/research/v2/s2-claude-plan.md)）。可摄入 QA 对、通过 FTS5 + 向量嵌入检索、与大模型进行带有 Wiki 记忆增强的对话——**DeepSeek** 负责公有聊天，**Ollama** 负责摄入管线、Wiki 编译和语义嵌入。

当前版本：[v0.1.0](CHANGELOG.md)。版本历史参见 [CHANGELOG.md](CHANGELOG.md)、[docs/roadmap.md](docs/roadmap.md) 和 [docs/adr/](docs/adr/)。文档结构入口参见 [docs/README-cn.md](docs/README-cn.md)。

## 功能概览

- **5 标签仪表盘**（比较 / QA 聊天 / RAG / LLM-Wiki / 库存）—— 并排展示原始 QA 流式输出、混合检索、蒸馏后的 Wiki 和系统资源使用情况
- `POST /chat` 通过 **DeepSeek**（SSE）流式回答，注入 Wiki 上下文；保存到记忆为**手动加入**
- `POST /ingest` 将 QA 对加入异步 Wiki 编译队列（通过 Ollama）
- `GET /query` 支持关键词、语义和混合三种搜索模式
- `GET /wiki/{slug}`、`GET /wiki/graph`、`GET /wiki/tree`、`GET /health`、`GET /stats`、`GET /inventory` 提供 Wiki 内容、图谱、目录树、服务状态和数据存储记录统计
- `wiki_search`、`wiki_ingest`、`wiki_get_page`、`wiki_stats` 通过 stdio MCP 服务器暴露，供 IDE 集成

## 架构

```
┌─────────────────────────────────────────────────────┐
│  浏览器 (http://localhost:3000)                      │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │   ChatWindow      │  │   WikiSidebar           │  │
│  │   (消息 + 输入栏)  │  │   (渲染 wiki.md 内容)   │  │
│  └────────┬─────────┘  └────────▲────────────────┘  │
│           │ POST /api/chat      │ GET /wiki/{slug}  │
└───────────┼──────────────────────┼──────────────────┘
            │ (Next.js Route       │ (直接 fetch)
            │  Handler 代理)       │
            ▼                      │
┌──────────────────────────────────┼─────────────────┐
│  FastAPI 后端 (localhost:8000)                      │
│                                                     │
│  POST /chat ──► 分类 ──► 检索 Wiki                   │
│       │            ──► 流式 DeepSeek (SSE)           │
│       │  (不自动保存 — 手动加入)                     │
│                                                     │
│  POST /ingest      ──► 异步 Ollama 蒸馏              │
│  GET  /query       ──► FTS5 + 向量混合搜索            │
│  GET  /wiki/{slug} ──► 读取 Wiki Markdown            │
│  GET  /wiki/graph  ──► Wiki 节点 + 边                 │
│  GET  /wiki/tree   ──► 侧边栏目录                     │
│  GET  /health      ──► 服务状态                       │
│  GET  /stats       ──► 聚合计数器                     │
│  MCP stdio         ──► wiki_search / wiki_ingest     │
└─────────────────────────────────────────────────────┘
```

## 仪表盘预览

前端通过标签式仪表盘标题栏提供五个视图。以下是各视图的截图。

| 比较（三阶段并排） | QA 聊天（DeepSeek 流式） |
|---|---|
| ![比较视图](assets/memweaver-compare.png) | ![QA 聊天视图](assets/memweaver-qa-chat.png) |

| RAG（混合检索） | LLM-Wiki（蒸馏记忆） |
|---|---|
| ![RAG 视图](assets/memweaver-rag.png) | ![LLM-Wiki 视图](assets/memweaver-llm-wiki.png) |

| 库存（记录计数 + Wiki 图谱） |
|---|
| ![库存视图](assets/memweaver-inventory.png) |

## 前置要求

- **Python 3.12+**（后端）
- **Node.js 20+** 和 **pnpm**（前端，[安装 pnpm](https://pnpm.io/installation)）
- **Ollama** 本地运行（`ollama serve`）并已拉取配置的模型

## 依赖安装

### 后端

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 前端

```bash
cd chat-app
pnpm install
```

## 本地运行

需要**三个**终端：

### 1. Ollama

```bash
ollama serve
```

如尚未拉取模型：

```bash
ollama pull qwen2.5:7b-instruct
```

### 2. 后端（FastAPI）

```bash
source venv/bin/activate
uvicorn server.main:app --reload
# http://localhost:8000
```

### 3. 前端（Next.js）

```bash
cd chat-app
pnpm dev
# http://localhost:3000
```

打开 `http://localhost:3000`，即可看到 **5 标签仪表盘**（比较、QA 聊天、RAG、LLM-Wiki、库存）。

## MCP 服务器（IDE 集成）

将 Wiki 记忆以 MCP 工具形式暴露给 Cursor、Claude Code 或 Opencode——无需运行 FastAPI 聊天栈。

### 前置要求

1. Ollama 运行中（`ollama serve`）且已拉取模型
2. Python 虚拟环境已安装（`pip install -r requirements.txt`）
3. **不要**在使用 MCP 摄入时运行 `uvicorn`（单个摄入工作器）

### 设置

1. 复制 [`mcp.json.example`](mcp.json.example) 到 `.cursor/mcp.json`（或添加到全局 MCP 配置）
2. 将 `cwd` 设置为该仓库的绝对路径
3. 重启 Cursor

### 工具

| 工具 | 用途 |
|------|------|
| `wiki_search` | 在已编译的 Wiki 上执行混合 FTS5 + 向量搜索 |
| `wiki_ingest` | 保存 QA 到异步 Wiki 编译管线 |
| `wiki_get_page` | 按 slug 获取完整 Markdown |
| `wiki_stats` | 知识库计数 + Ollama 可达性 |

## 使用指南

### 聊天（主界面 — 推荐起始点）

1. 在浏览器中打开 `http://localhost:3000`
2. 使用标签栏在五个视图间切换：
   - **比较** — 并排查看 QA 聊天、RAG 和 LLM-Wiki 面板
   - **QA 聊天** — 输入问题，通过 DeepSeek 获取带有 Wiki 上下文注入的流式回答（主聊天流程）
   - **RAG** — 查询混合 BM25 + sqlite-vec 检索层
   - **LLM-Wiki** — 关键词搜索蒸馏后的 Wiki Markdown
   - **库存** — 浏览所有数据存储的记录计数和交互式 Wiki 图谱
3. 在 **QA 聊天**中：后端对问题进行分类（coding / design / ml / business / general），检索最相关的 Wiki 页面，将其注入为上下文，并通过 DeepSeek SSE 逐 token 流式输出
4. 右侧边栏显示正在使用的 Wiki 文章——可以检查 LLM 正在参考哪些知识
5. 回答完成后，会出现 **"Save to memory"** 复选框。勾选（可选添加备注）并点击保存，即可将问答持久化到 Wiki。保存为手动加入——不会自动编译任何内容。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat` | 带 Wiki 上下文注入的流式聊天（SSE 通过 DeepSeek，手动保存） |
| `GET` | `/wiki/{slug}` | 获取 Wiki 文章 Markdown 内容 |
| `GET` | `/wiki/graph` | Wiki 页面作为节点 + wikilink 边（用于图谱可视化） |
| `GET` | `/wiki/tree` | 基于 `wiki/index.md` 的侧边栏友好目录 |
| `POST` | `/ingest` | 提交 QA 对进行异步摄入（返回 202） |
| `GET` | `/query` | 三种模式搜索已摄入的知识 |
| `GET` | `/health` | 服务健康 + Ollama + 数据库状态 |
| `GET` | `/stats` | 聚合计数器（摄入次数、Wiki 页面、标签） |

### 知识摄入

通过 API 直接摄入将原始 QA 对送入管线。可用于从现有文档或 Agent 对话中填充 Wiki：

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是 RAG？", "answer": "RAG 是检索增强生成，将检索器与 LLM 生成器相结合。", "source": "manual"}'
```

返回 `202 Accepted` 和 `ingest_id`。后台工作器随后：

1. **总结** — Ollama 将 QA 蒸馏为原子 + 关键声明 + 主题
2. **写入** — 不可变原始 JSON 到 `raw/qa/<date>/`，Wiki Markdown 到 `wiki/concepts/`
3. **索引** — 更新 SQLite `pages` + `qa_pairs` 表并重建 FTS5 索引
4. **嵌入** — 通过 Ollama 调用 `nomic-embed-text`，将 768 维向量存入 `page_embeddings` vec0 表（启用语义搜索）
5. **链接** — 解析 `[[wikilinks]]`，更新 Wiki 图谱和入链计数
6. **检测矛盾** — 将新原子与现有声明比较，在冲突时追加 `> ⚠️` 块引用

可通过 `GET /stats` 或 `GET /query?q=...` 轮询确认管线完成。

### 搜索知识

搜索端点支持三种模式，通过 `mode` 参数选择：

```bash
# 关键词模式 — FTS5 BM25（确定性，零 Ollama 开销）
curl "http://localhost:8000/query?q=attention+mechanism&mode=keyword"

# 语义模式 — 向量余弦相似度（捕捉概念匹配）
curl "http://localhost:8000/query?q=how+do+models+weigh+token+relevance&mode=semantic"

# 混合模式 — FTS5 + 向量通过倒数秩融合合并（默认）
curl "http://localhost:8000/query?q=attention+mechanism&mode=hybrid&limit=5"
```

**三种模式的区别：**

| 模式 | 使用场景 | 工作原理 |
|------|---------|---------|
| `keyword` | 需要精确匹配——搜索"RAG"应找到 RAG 页面 | FTS5 BM25 在 `pages_fts` 上。快速、确定、无 Ollama 调用 |
| `semantic` | 需要概念匹配——搜索"测试方法论"应找到"冒烟测试" | 通过 Ollama 嵌入查询，然后在 `page_embeddings` vec0 表中按余弦距离查找最近邻 |
| `hybrid`（默认） | 两者兼具——精确关键词精度 + 语义广度 | 并行执行关键词和语义搜索，通过倒数秩融合（k=60）合并结果 |

### 为已有页面回填嵌入

如果 Wiki 中已存在页面（来自之前的摄入），运行回填脚本生成其嵌入：

```bash
python3 scripts/backfill_embeddings.py
```

该脚本读取 `pages` 表中的每个页面，通过 Ollama 调用 `nomic-embed-text`，将向量更新到 `page_embeddings` 中。运行后，所有现有页面可通过 `mode=semantic` 或 `mode=hybrid` 搜索。脚本是幂等的——多次运行安全。

### 验证管线

启动服务器后，确认一切连接正常：

```bash
# 基本健康检查
curl http://localhost:8000/health
# → {"status":"ok","ollama":"reachable","db":"ok","wiki_pages":4,"qa_pairs":4}

# 检查 Wiki 内容
curl http://localhost:8000/wiki/geo%20-%20geography

# 摄入测试 QA
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question":"什么是 Transformer？","answer":"Transformer 使用自注意力机制。","source":"test"}'

# 查询所有模式
curl "http://localhost:8000/query?q=transformer&mode=keyword"
curl "http://localhost:8000/query?q=neural+network+architecture&mode=semantic"
curl "http://localhost:8000/query?q=attention&mode=hybrid"
```

## 配置

运行时配置使用 **pydantic-settings**（环境变量和可选的 `.env`）。参见 [`.env.example`](.env.example)。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_NAME` | `LLM-Wiki Middleware Delegator` | FastAPI 标题 |
| `APP_ENV` | `development` | 环境标签 |
| `HOST` | `127.0.0.1` | 绑定地址 |
| `PORT` | `8000` | 绑定端口 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥（公有聊天 LLM） |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 聊天模型 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1/chat/completions` | 聊天补全端点 |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama 基础 URL |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | 用于总结 + Wiki 正文的模型 |
| `OLLAMA_TIMEOUT` | `120` | HTTP 超时（秒） |
| `WIKI_DIR` | `wiki` | Markdown 知识库根目录 |
| `RAW_DIR` | `raw/qa` | 不可变 QA JSON 根目录 |
| `DB_PATH` | `db/wiki.db` | SQLite 数据库路径 |
| `MAX_QUEUE_SIZE` | `100` | 摄入队列深度达到此值后返回 `503` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | 前端获取 Wiki 的后端 URL |

示例：

```bash
OLLAMA_MODEL=qwen2.5:7b-instruct uvicorn server.main:app --reload
```

## 冒烟测试

在 **uvicorn** 运行中的情况下：

```bash
./scripts/smoke-check.sh
```

该脚本依次调用 `GET /health`、`GET /stats`、`GET /query`、`POST /ingest`（期待 **202**），然后 `GET /query?q=smoke`。如有需要，可用 `BASE_URL` 覆盖基础 URL。

摄入后，轮询 `GET /stats` 或 `GET /query?q=...` 直到新数据出现（管线是异步的）。

## 项目结构

```
├── server/          # FastAPI 后端
│   ├── main.py      # 路由：/ingest, /chat, /query, /wiki/*, /health, /stats
│   ├── models/      # Pydantic 请求/响应模式
│   ├── services/    # 分类器、DeepSeek 客户端、公有 LLM、Wiki 检索器等
│   ├── pipeline/    # 摄入工作器、FTS、向量搜索、嵌入器、语义搜索
│   ├── config/      # pydantic-settings
│   └── db/          # SQLite + FTS5 + sqlite-vec
├── assets/           # 仪表盘截图、品牌资产
├── chat-app/         # Next.js 16 前端
│   ├── app/
│   │   ├── page.tsx           # 5 标签仪表盘
│   │   ├── api/chat/route.ts  # SSE 代理路由处理器
│   │   └── layout.tsx         # 根布局
│   └── components/            # 各面板和 UI 组件
├── wiki/            # LLM-Wiki Markdown 知识库
├── raw/             # 不可变 QA JSON 制品
├── docs/            # 计划、规格、设计文档
└── tests/           # Pytest 测试套件
```
