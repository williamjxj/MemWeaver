# mem-weaver Chat App

Chat frontend for the **mem-weaver** dual-LLM memory system. Sends questions to the FastAPI backend, streams responses via SSE, and displays rich markdown output with wiki memory context.

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

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

- **SSE streaming** — Tokens arrive one by one, rendered incrementally
- **Markdown output** — Assistant responses render with `react-markdown` (GFM: tables, lists, code blocks, links)
- **Wiki sidebar** — After each chat, the relevant wiki article is shown in the side panel
- **Auto-ingest** — Every Q&A is compiled into the wiki in the background (Phase B)

## Stack

- **Next.js 16** (App Router)
- **Tailwind CSS 4** + shadcn/ui
- **react-markdown** + **remark-gfm** for rich output
- **TypeScript**
