# mem-weaver Chat App

📖 [English](README.md) · [中文](README-cn.md)

Chat frontend for the **mem-weaver** dual-LLM memory system. Sends questions to the FastAPI backend, streams responses via SSE, renders rich markdown output with wiki memory context, and provides a 5-tab dashboard for exploring the full pipeline.

## Dashboard

| Compare (all stages side by side) | QA Chat (DeepSeek streaming) |
|---|---|
| ![Compare view](../assets/memweaver-compare.png) | ![QA Chat view](../assets/memweaver-qa-chat.png) |

| RAG (hybrid retrieval) | LLM-Wiki (distilled memory) |
|---|---|
| ![RAG view](../assets/memweaver-rag.png) | ![LLM-Wiki view](../assets/memweaver-llm-wiki.png) |

| Inventory (record counts + wiki graph) |
|---|
| ![Inventory view](../assets/memweaver-inventory.png) |

## Features

- **5-tab dashboard** — switch between Compare, QA Chat, RAG, LLM-Wiki, and Inventory views
- **SSE streaming** — Tokens arrive one by one, rendered incrementally via DeepSeek
- **Markdown output** — Assistant responses render with `react-markdown` (GFM: tables, lists, code blocks, links)
- **Wiki sidebar** — After each chat, the relevant wiki article is shown in the side panel
- **RAG + LLM-Wiki panels** — query the hybrid BM25/sqlite-vec retrieval layer or keyword-search the distilled wiki
- **Inventory panel** — browse record counts across raw QA, wiki concepts, database tables, index, and log — with an interactive force-directed wiki graph
- **Opt-in save to memory** — save Q&A turns to the wiki only when you choose (with optional notes)

## Stack

- **Next.js 16** (App Router)
- **Tailwind CSS 4** + shadcn/ui
- **react-markdown** + **remark-gfm** for rich output
- **TypeScript**

## Getting Started

Make sure the FastAPI backend is running first (from repo root):

```bash
uvicorn server.main:app --reload
```

Then start the frontend:

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser and use the tab bar to explore each view.

## Production Build

```bash
pnpm build
```
