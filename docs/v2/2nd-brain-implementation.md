
# Second Brain: Dual-LLM Memory System
## Implementation Plan (MacBook Pro)

**Summary:**
This document describes a modular, production-ready architecture for a local+cloud "second brain" memory system. It combines a FastAPI delegator, local Ollama LLM for wiki-style memory compilation, and a public LLM for reasoning. Knowledge is incrementally distilled into a Markdown wiki, indexed and retrieved by topic, and injected into future prompts for context-efficient, consistent answers. The design is inspired by Karpathy's LLM-wiki, Agent Skills, and recent memoryLLM research.

> **Core concept:** A local FastAPI "Delegator" sits between your Chat App and the cloud LLM.
> After every Q+A turn, a local Ollama model compiles the exchange into an LLM-wiki-style
> knowledge entry, categorized using Agent-Skills taxonomy. On the next turn, only the
> relevant compiled summary — not raw history — is injected as context. The wiki grows
> incrementally. Memory is never lost; context windows never bloat.

---


## 1. Architecture Overview


**Key insight:**
Public LLM APIs are stateless. Instead of replaying raw chat history (token bloat, context loss), this system uses a local LLM to synthesize each Q+A into a dense, structured wiki entry. The public LLM always receives the distilled essence of prior knowledge, not the noise. (Karpathy: "memory shouldn't be retrieval — it should be synthesis.")


### Two-phase per-turn design

**Phase A (sync, user-facing):**
User → Chat App → Delegator → retrieve Sk from WikiStore → Q + Sk → Public LLM → An → User

**Phase B (async, background):**
Delegator (background task) → Ollama Value Gate → Ollama Compiler → WikiStore update

The user never waits for Phase B. The wiki silently improves after each turn.


#### Memory evolution across turns

    Turn 1:  Q1 → Public LLM → A1
                  ↓ (async)
              Ollama compiles S1
              WikiStore: coding/llm-memory.md created

    Turn 2:  Q2 + S1 → Public LLM → A2
                  ↓ (async)
              Ollama merges Q2+A2 into S1 → S2
              WikiStore: coding/llm-memory.md updated (v2)

    Turn 3:  Q3 + S2 (if same topic) → Public LLM → A3
           or Q3 + S_design (if diff topic) → Public LLM → A3

---


## 2. Technology Stack


### Local stack (MacBook Pro)

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Chat frontend | **Next.js** | 14 (App Router) | User interface, WikiSidebar |
| API gateway / orchestrator | **FastAPI** | 0.115+ | Delegator service |
| Runtime | **Python** | 3.12 | Backend language |
| Package manager | **uv** | latest | Fast Python deps |
| Local LLM runtime | **Ollama** | latest | Serves local model |
| Wiki compiler model | **llama3.2:3b** or **mistral:7b** | — | Summarization, classification |
| Semantic search (phase 2) | **nomic-embed-text** via Ollama | — | Embedding-based retrieval |
| Vector store (phase 2) | **sqlite-vec** | 0.1.9 | Local semantic search via vec0 extension, 768-d nomic-embed-text embeddings |
| Wiki storage | **Markdown files + git** | — | Human-readable, versioned |
| Wiki index | `_index.md` keyword table | — | Zero-latency routing |
| Wiki GUI | **Obsidian** | latest | Browse/edit wiki |
| Background tasks | **FastAPI BackgroundTasks** | built-in | Non-blocking Phase B |
| Graph memory (phase 3) | **Graphiti / Zep** | latest | Knowledge graph overlay |


#### Model selection by Mac RAM

| Mac RAM | Recommended Ollama model | Compilation quality |
|---------|--------------------------|---------------------|
| 8 GB | `llama3.2:3b` | Good — fast, handles summarization |
| 16 GB | `mistral:7b` or `llama3.1:8b` | Better — nuanced extraction |
| 32 GB+ | `qwen2.5:14b` or `llama3.3:70b` | Near-cloud quality locally |

```bash
brew install ollama
ollama serve                        # starts on localhost:11434
ollama pull llama3.2:3b             # wiki compiler
ollama pull nomic-embed-text        # embeddings (phase 2)
```


### Cloud / External APIs

| Service | Model | Role | Notes |
|---------|-------|------|-------|
| **Anthropic** | claude-sonnet-4-* | Primary reasoning engine | Best instruction following |
| **OpenAI** | gpt-4o | Fallback / A-B comparison | Compatible API format |
| **MiniMax** | MiniMax-Text-01 | Long-context, cheaper | 1M token context window |


### Optional Enhancement Tools

| Tool | Purpose | When to add |
|------|---------|-------------|
| **LangChain** | Memory chain abstractions | If you want pre-built ConversationSummaryMemory |
| **LlamaIndex** | Vector-based retrieval pipeline | When keyword matching isn't enough |
| **Mem0 / Zep** | Drop-in memory layer with graph | Phase 3 alternative to custom Graphiti |
| **Hindsight** | Local memory engine (Ollama-based) | Reference implementation to study |
| **Obsidian** | Human wiki browser + editor | Immediately useful for debugging |
| **Gitea** (self-hosted) | Remote wiki backup | Optional, for persistence across machines |

---


## 3. Repository Structure (Example)

```
second-brain/
│
├── delegator/                          ← FastAPI backend (the orchestrator)
│   ├── main.py                         ← app entrypoint, /chat route
│   ├── config.py                       ← env vars via pydantic-settings
│   ├── services/
│   │   ├── classifier.py               ← Agent-Skills topic routing (keyword + Ollama fallback)
│   │   ├── wiki_retriever.py           ← reads _index.md, returns relevant Sk
│   │   ├── wiki_compiler.py            ← Ollama Phase B: value gate + compile/merge
│   │   ├── public_llm.py               ← Anthropic/OpenAI client with wiki injection
│   │   └── embedder.py                 ← optional: nomic-embed-text for semantic search
│   ├── prompts/
│   │   ├── value_gate.txt              ← "Is this Q+A worth compiling? SKIP or PROCESS"
│   │   ├── compiler.txt                ← "Rewrite wiki page integrating new insight"
│   │   └── classifier.txt              ← "Classify question: coding/design/ml/business"
│   └── pyproject.toml
│
├── wiki/                               ← LLM-wiki knowledge store (its own git repo)
│   ├── _index.md                       ← master routing table: slug → keywords → summary
│   ├── coding/
│   │   ├── python-patterns.md          ← e.g. "User prefers FastAPI + async, avoids ORMs"
│   │   ├── llm-integration.md          ← e.g. "Anthropic client uses httpx, retries on 429"
│   │   └── testing-strategy.md
│   ├── design/
│   │   ├── system-architecture.md      ← e.g. "Delegator pattern: local gateway before cloud"
│   │   └── api-design.md
│   ├── ml/
│   │   ├── rag-patterns.md             ← e.g. "RAG uses nomic-embed-text, top-3 chunks"
│   │   ├── memory-mechanisms.md        ← e.g. "Dual-LLM: Ollama compiles, Claude reasons"
│   │   └── agent-skills.md
│   ├── business/
│   │   └── project-context.md          ← e.g. "AgenticOmni: bidding engine, due Q3 2026"
│   └── general/
│       └── user-preferences.md         ← e.g. "Prefers bullet points, code examples, concise"
│
├── chat-app/                           ← Next.js frontend
│   ├── app/
│   │   ├── page.tsx                    ← main chat view
│   │   └── api/chat/route.ts           ← proxies to delegator
│   └── components/
│       ├── ChatWindow.tsx
│       └── WikiSidebar.tsx             ← shows active wiki slug and preview
│
├── .env.local                          ← secrets (never commit)
├── docker-compose.yml                  ← optional local dev container
├── CLAUDE.md                           ← project context for Claude Code / Cursor
└── README.md
```

---


## 4. Agent-Skills Taxonomy (Topic Router)

Inspired by [agentskills.io](https://agentskills.io): questions trigger skill categories
via keyword matching. Each category maps to one or more wiki files.


### Fixed taxonomy (expand to dynamic later)

```python
# services/classifier.py

SKILL_TAXONOMY = {
    "coding": {
        "keywords": ["python", "code", "function", "class", "api", "debug", "error",
                     "import", "fastapi", "typescript", "async", "test", "deploy",
                     "docker", "git", "bash", "script", "library", "package"],
        "wiki_paths": ["coding/python-patterns", "coding/llm-integration",
                       "coding/testing-strategy"],
    },
    "design": {
        "keywords": ["architecture", "system", "design", "pattern", "microservice",
                     "schema", "database", "endpoint", "structure", "flow", "diagram"],
        "wiki_paths": ["design/system-architecture", "design/api-design"],
    },
    "ml": {
        "keywords": ["llm", "model", "rag", "embedding", "prompt", "token", "context",
                     "fine-tune", "inference", "agent", "memory", "vector", "attention",
                     "transformer", "ollama", "anthropic", "openai"],
        "wiki_paths": ["ml/rag-patterns", "ml/memory-mechanisms", "ml/agent-skills"],
    },
    "business": {
        "keywords": ["deadline", "client", "project", "budget", "meeting", "requirement",
                     "stakeholder", "roadmap", "sprint", "feature", "cost", "roi"],
        "wiki_paths": ["business/project-context"],
    },
    "general": {
        "keywords": [],  # fallback
        "wiki_paths": ["general/user-preferences"],
    },
}

def classify_topic(question: str) -> tuple[str, list[str]]:
    """Returns (topic_name, list_of_wiki_slugs). Fast, zero-latency."""
    q = question.lower()
    scores = {
        topic: sum(1 for kw in data["keywords"] if kw in q)
        for topic, data in SKILL_TAXONOMY.items()
    }
    best_topic = max(scores, key=scores.get)
    if scores[best_topic] == 0:
        best_topic = "general"
    return best_topic, SKILL_TAXONOMY[best_topic]["wiki_paths"]
```

When keyword score = 0, escalate to Ollama for LLM-based classification (adds ~1s):

```python
async def classify_with_ollama(question: str) -> str:
    resp = await ollama_client.post("/api/generate", json={
        "model": OLLAMA_MODEL,
        "prompt": (
            f'Classify into ONE category: coding / design / ml / business / general\n'
            f'Question: "{question}"\n'
            f'Reply with only the category word.'
        ),
        "stream": False,
    })
    result = resp.json()["response"].strip().lower()
    return result if result in SKILL_TAXONOMY else "general"
```

---


## 5. Wiki Store Design (LLM-wiki format)


### `_index.md` — master routing table

```markdown
---
title: "Second Brain Wiki Index"
updated: 2026-04-22
total_articles: 8
---

# Wiki Index

| Slug | Topic | Keywords | One-line summary |
|------|-------|----------|-----------------|
| coding/python-patterns | coding | fastapi, async, pydantic, uv | User prefers FastAPI 0.115 + async routes; avoids sync DB calls |
| coding/llm-integration | coding | anthropic, ollama, httpx, token | Anthropic client via httpx; Ollama on :11434; retries on 429 |
| ml/memory-mechanisms | ml | memory, wiki, dual-llm, ollama | Dual-LLM: Ollama compiles wiki, Claude reasons over summaries |
| ml/rag-patterns | ml | rag, embedding, vector, chroma | nomic-embed-text locally; top-3 chunk retrieval; ChromaDB |
| design/system-architecture | design | architecture, delegator, gateway | Delegator pattern: local gateway classifies before cloud LLM |
| business/project-context | business | agentomni, bidding, deadline | AgenticOmni bidding engine: vector search, due Q3 2026 |
| general/user-preferences | general | prefer, style, format, concise | Prefers bullet points, code examples, concise answers |
```


### Individual article format (LLM-wiki spec)

Every article follows the same schema so Ollama can merge reliably:

```markdown
---
title: "ML memory mechanisms"
slug: ml/memory-mechanisms
tags: [memory, llm, ollama, wiki, dual-llm, summarization]
aliases: [second brain, memory manager, knowledge compiler]
related: [ml/rag-patterns, design/system-architecture]
updated: 2026-04-22
version: 4
---

# ML memory mechanisms

> **One-liner**: Dual-LLM architecture where Ollama (local) compiles Q+A pairs into
> LLM-wiki articles incrementally; Claude (cloud) reasons over retrieved summaries, never raw history.

## Facts

- Ollama runs on localhost:11434; used for Phase B (async, non-blocking) wiki compilation only
- Public LLM (Claude) receives: Q_new + retrieved wiki article Sk (not raw chat history)
- Value Gate prompt filters noise: only PROCESS if Q+A contains reusable technical facts
- Wiki articles versioned with `.bak.md` copies before each Ollama rewrite
- Memory never bloats: each article caps at 3,000 chars before injection (truncated at end)
- Topic routing: keyword match on `_index.md` → O(n) scan < 2ms; Ollama fallback if score=0
- Ollama compilation: 8-20s (mistral:7b); runs as FastAPI BackgroundTask post-response

## Architecture

The system has two phases per user turn:
- **Phase A (synchronous)**: retrieve Sk → inject into prompt → call Public LLM → return An
- **Phase B (async)**: send Q+An to Ollama → value gate → if PROCESS: merge into wiki article

After N turns on the same topic, the article becomes a dense technical reference replacing all raw history.

## Prompts

Value Gate prompt instructs Ollama to return `SKIP` or `PROCESS + keywords`.
Compiler prompt instructs Ollama to rewrite the existing article in LLM-wiki format,
preserving all existing facts and adding new ones under relevant sections.

## Gotchas

- Ollama BackgroundTask shares process with other tasks — only queue one compilation at a time
- Over-compression: if Ollama summarizes too aggressively, add "Preserve all existing technical
  detail verbatim. Only ADD, never REMOVE" to compiler prompt
- Index drift: if `_index.md` desyncs, run `/admin/rebuild-index` to rescan all article files
- Wrong topic retrieval: if keyword score is tied, take the topic whose wiki article is larger
  (more established = more relevant)
- Context injection cap: truncate Sk at 3,000 chars to leave room for Q_new in prompt

## Related

- [[design/system-architecture]] — the full delegator flow with Phase A and B timing
- [[ml/rag-patterns]] — alternative retrieval using embeddings instead of keyword index
```

---


## 6. Core Service Implementations (Key Snippets)

### 6.1 `main.py` — FastAPI Delegator

```python
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx
from pydantic import BaseModel
from config import settings
from services.classifier import classify_topic, classify_with_ollama
from services.wiki_retriever import retrieve_summary
from services.public_llm import ask_public_llm
from services.wiki_compiler import compile_wiki_async

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=90)
    yield
    await app.state.http.aclose()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    topic: str
    wiki_slug: str | None
    context_chars: int

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    # Step 1: Classify topic (fast keyword match, Ollama fallback)
    topic, slugs = classify_topic(req.question)
    if not any(slugs):
        topic = await classify_with_ollama(req.question)
        slugs = SKILL_TAXONOMY[topic]["wiki_paths"]

    # Step 2: Retrieve most relevant wiki summary (Phase A)
    slug, summary = await retrieve_summary(req.question, slugs)

    # Step 3: Ask public LLM with wiki context injected (Phase A)
    answer = await ask_public_llm(req.question, summary)

    # Step 4: Compile wiki in background (Phase B — non-blocking)
    background_tasks.add_task(
        compile_wiki_async,
        question=req.question,
        answer=answer,
        topic=topic,
        slug=slug,
    )

    return ChatResponse(
        answer=answer,
        topic=topic,
        wiki_slug=slug,
        context_chars=len(summary),
    )

@app.get("/wiki/{slug:path}")
async def get_wiki(slug: str):
    """Frontend can display the active wiki article."""
    from pathlib import Path
    p = Path(settings.wiki_dir) / f"{slug}.md"
    return {"content": p.read_text() if p.exists() else ""}

@app.post("/admin/rebuild-index")
async def rebuild_index():
    """Resync _index.md from all article files."""
    from services.wiki_compiler import rebuild_index_from_articles
    await rebuild_index_from_articles()
    return {"status": "rebuilt"}
```

### 6.2 `wiki_retriever.py` — Fast Keyword Retrieval

```python
from pathlib import Path
from config import settings

WIKI_DIR = Path(settings.wiki_dir)
INDEX_FILE = WIKI_DIR / "_index.md"
MAX_SUMMARY_CHARS = 3000  # injection cap

def _load_index() -> list[dict]:
    rows = []
    for line in INDEX_FILE.read_text().splitlines():
        if line.startswith("| ") and "---" not in line and "Slug" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4:
                rows.append({
                    "slug": parts[0],
                    "topic": parts[1],
                    "keywords": [k.strip().lower() for k in parts[2].split(",")],
                    "summary": parts[3],
                })
    return rows

async def retrieve_summary(question: str, candidate_slugs: list[str]) -> tuple[str | None, str]:
    """Return (best_slug, summary_text) for injection into public LLM prompt."""
    index = _load_index()
    q_lower = question.lower()

    # Score candidate articles by keyword overlap with question
    scored = []
    for entry in index:
        if entry["slug"] in candidate_slugs:
            score = sum(1 for kw in entry["keywords"] if kw in q_lower)
            scored.append((score, entry))

    if not scored:
        return None, ""

    best = max(scored, key=lambda x: x[0])
    slug = best[1]["slug"]

    article_path = WIKI_DIR / f"{slug}.md"
    if not article_path.exists():
        return slug, best[1]["summary"]

    content = article_path.read_text()
    # Truncate to injection cap (from the end of ## Facts section, preserving frontmatter)
    return slug, content[:MAX_SUMMARY_CHARS]
```

### 6.3 `public_llm.py` — Anthropic Client with Wiki Injection

```python
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

INJECTION_TEMPLATE = """\
You have structured background knowledge about this user and their projects. \
Use it as established context to give consistent, informed answers. \
Do not repeat this context back to the user.

---
{summary}
---"""

async def ask_public_llm(question: str, wiki_summary: str) -> str:
    messages = []

    if wiki_summary.strip():
        # Inject wiki as a priming exchange — avoids system_prompt token overhead
        messages.append({
            "role": "user",
            "content": INJECTION_TEMPLATE.format(summary=wiki_summary)
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I have that context ready."
        })

    messages.append({"role": "user", "content": question})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=messages,
    )
    return response.content[0].text
```

### 6.4 `wiki_compiler.py` — Ollama Phase B (Background Task)

```python
import httpx
import datetime
from pathlib import Path
from config import settings

WIKI_DIR = Path(settings.wiki_dir)
OLLAMA_URL = f"{settings.ollama_base_url}/api/generate"

VALUE_GATE = """\
Act as a Knowledge Sieve. Review this Q+A exchange.
Determine if it contains: new technical facts, project decisions, user preferences, \
or reusable patterns worth storing long-term.

If it is purely conversational, repetitive, or contains no durable knowledge → reply: SKIP
If it is valuable → reply: PROCESS
Then on a new line list exactly 3 keywords (comma-separated, lowercase).

Q: {question}
A: {answer}

Reply with SKIP or PROCESS + keywords only."""

COMPILER = """\
You are an expert technical writer maintaining an LLM-optimized wiki.
Your task: rewrite the existing wiki page to integrate a new Q+A insight.

EXISTING WIKI PAGE:
{existing}

NEW Q+A TO INTEGRATE:
Q: {question}
A: {answer}

RULES:
1. Keep frontmatter block (---) intact; update `updated` date; increment `version` by 1.
2. Preserve ALL existing technical facts verbatim — never remove content.
3. Add new information under the most relevant existing section, or create a new section.
4. Every sentence must be assertion-dense: specific values, names, commands, decisions.
5. Keep ## Facts, ## Gotchas, ## Related sections.
6. If this is a new article (existing is empty), create a complete LLM-wiki article from scratch.

Output ONLY the complete updated markdown. No preamble. No explanation."""

async def compile_wiki_async(question: str, answer: str, topic: str, slug: str | None):
    """Phase B: run after answer returned to user. Never blocks the user."""
    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: Value gate
        gate_resp = await client.post(OLLAMA_URL, json={
            "model": settings.ollama_model,
            "prompt": VALUE_GATE.format(question=question, answer=answer),
            "stream": False,
        })
        gate_text = gate_resp.json()["response"].strip().upper()

        if gate_text.startswith("SKIP"):
            return  # Nothing worth storing

        # Parse keywords from gate response
        keywords = []
        lines = gate_text.splitlines()
        if len(lines) > 1:
            keywords = [k.strip().lower() for k in lines[1].split(",")][:5]

        # Step 2: Resolve target slug
        if not slug:
            kw_slug = keywords[0].replace(" ", "-") if keywords else "general"
            slug = f"{topic}/{kw_slug}"

        article_path = WIKI_DIR / f"{slug}.md"
        article_path.parent.mkdir(parents=True, exist_ok=True)
        existing = article_path.read_text() if article_path.exists() else ""

        # Step 3: Backup existing version
        if existing:
            version = _get_version(existing)
            backup = article_path.with_suffix(f".v{version}.bak.md")
            backup.write_text(existing)

        # Step 4: Compile updated article via Ollama
        compile_resp = await client.post(OLLAMA_URL, json={
            "model": settings.ollama_model,
            "prompt": COMPILER.format(
                existing=existing or "(new article — create from scratch)",
                question=question,
                answer=answer,
            ),
            "stream": False,
        })
        updated = compile_resp.json()["response"].strip()

        # Strip any ```markdown fences Ollama might add
        if updated.startswith("```"):
            updated = "\n".join(updated.splitlines()[1:])
            if updated.endswith("```"):
                updated = updated[:-3]

        article_path.write_text(updated.strip())

        # Step 5: Update _index.md
        _upsert_index(slug, topic, keywords, updated)

        # Step 6: Git commit (optional)
        _git_commit(slug)

def _get_version(content: str) -> int:
    for line in content.splitlines():
        if line.strip().startswith("version:"):
            try:
                return int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pass
    return 1

def _extract_oneliner(content: str) -> str:
    for line in content.splitlines():
        if "**One-liner**" in line:
            return line.replace("> **One-liner**:", "").strip()[:80]
    return "See article."

def _upsert_index(slug: str, topic: str, keywords: list[str], content: str):
    index_path = WIKI_DIR / "_index.md"
    if not index_path.exists():
        index_path.write_text(_empty_index())

    summary = _extract_oneliner(content)
    kw_str = ", ".join(keywords[:5])
    new_row = f"| {slug} | {topic} | {kw_str} | {summary} |"

    lines = index_path.read_text().splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"| {slug} |"):
            lines[i] = new_row
            updated = True
            break
    if not updated:
        lines.append(new_row)

    index_path.write_text("\n".join(lines))

def _git_commit(slug: str):
    import subprocess
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(WIKI_DIR), capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"wiki: update {slug}"],
            cwd=str(WIKI_DIR), capture_output=True
        )
    except Exception:
        pass  # Git is optional — don't crash if not initialized

async def rebuild_index_from_articles():
    """Admin: rescan all .md files and regenerate _index.md."""
    index_path = WIKI_DIR / "_index.md"
    rows = ["| Slug | Topic | Keywords | One-line summary |", "|------|-------|----------|-----------------|"]
    for article in WIKI_DIR.rglob("*.md"):
        if article.name.startswith("_") or ".bak" in article.name:
            continue
        slug = str(article.relative_to(WIKI_DIR)).replace(".md", "")
        topic = slug.split("/")[0]
        content = article.read_text()
        oneliner = _extract_oneliner(content)
        rows.append(f"| {slug} | {topic} | (rescan) | {oneliner} |")
    header = index_path.read_text().split("| Slug |")[0]
    index_path.write_text(header + "\n".join(rows))

def _empty_index() -> str:
    return f"""---
title: "Second Brain Wiki Index"
updated: {datetime.date.today().isoformat()}
total_articles: 0
---

# Wiki Index

| Slug | Topic | Keywords | One-line summary |
|------|-------|----------|-----------------|
"""
```

### 6.5 `config.py` — Settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    wiki_dir: str = "../wiki"

    class Config:
        env_file = ".env.local"

settings = Settings()
```

---


## 7. Chat App Frontend (Next.js)

### Key component: ChatWindow with WikiSidebar

```typescript
// app/page.tsx
"use client";
import { useState } from "react";
import { WikiSidebar } from "@/components/WikiSidebar";

interface Message { role: "user" | "assistant"; content: string; }

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [activeTopic, setActiveTopic] = useState<string>("");
  const [loading, setLoading] = useState(false);

  async function send() {
    if (!input.trim()) return;
    const q = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: q }]);
    setLoading(true);

    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const data = await res.json();

    setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
    setActiveSlug(data.wiki_slug);
    setActiveTopic(data.topic);
    setLoading(false);
  }

  return (
    <div className="flex h-screen">
      <main className="flex-1 flex flex-col p-4 gap-2">
        <div className="flex-1 overflow-y-auto space-y-3">
          {messages.map((m, i) => (
            <div key={i} className={`p-3 rounded-lg text-sm ${
              m.role === "user" ? "bg-blue-50 ml-8" : "bg-gray-50 mr-8"
            }`}>
              {m.content}
            </div>
          ))}
          {loading && <div className="text-gray-400 text-sm">Thinking...</div>}
        </div>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Ask anything..."
            className="flex-1 border rounded p-2 text-sm"
          />
          <button onClick={send} className="px-4 py-2 bg-blue-600 text-white rounded text-sm">
            Send
          </button>
        </div>
      </main>
      <WikiSidebar slug={activeSlug} topic={activeTopic} />
    </div>
  );
}
```

```typescript
// components/WikiSidebar.tsx
"use client";
import { useEffect, useState } from "react";

export function WikiSidebar({ slug, topic }: { slug: string | null; topic: string }) {
  const [content, setContent] = useState("");

  useEffect(() => {
    if (!slug) return;
    fetch(`http://localhost:8000/wiki/${slug}`)
      .then(r => r.json())
      .then(d => setContent(d.content));
  }, [slug]);

  return (
    <aside className="w-80 border-l bg-gray-50 flex flex-col">
      <div className="p-3 border-b bg-white">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Active context</p>
        <p className="text-sm font-mono text-blue-700">{slug ?? "none"}</p>
        <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
          {topic}
        </span>
      </div>
      <pre className="flex-1 overflow-y-auto p-3 text-xs text-gray-600 whitespace-pre-wrap font-mono">
        {content || "No wiki context loaded."}
      </pre>
    </aside>
  );
}
```

---


## 8. Running the Full Stack

```bash
# ── Terminal 1: Ollama ──────────────────────────────────────────
ollama serve

# ── Terminal 2: Delegator ───────────────────────────────────────
cd delegator
uv venv && source .venv/bin/activate
uv add fastapi uvicorn httpx anthropic pydantic-settings
uv run uvicorn main:app --reload --port 8000

# ── Terminal 3: Chat App ────────────────────────────────────────
cd chat-app
pnpm install
pnpm dev                              # http://localhost:3000

# ── Terminal 4: Obsidian (optional) ────────────────────────────
# Open Obsidian → "Open folder as vault" → select ./wiki/
# Now you can browse, search, and manually edit wiki articles

# ── Initialize wiki git repo ────────────────────────────────────
cd wiki
git init
git add .
git commit -m "init: empty wiki"
```

### `.env.local`

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
WIKI_DIR=../wiki
```

---


## 9. Implementation Phases

### Phase 1 — Working prototype (2-3 days)
- [ ] FastAPI delegator with `/chat` endpoint
- [ ] Keyword-based `classify_topic()` with fixed taxonomy
- [ ] `retrieve_summary()` reading `_index.md`
- [ ] `ask_public_llm()` with wiki priming injection
- [ ] Hand-write 2-3 seed wiki articles to test retrieval
- [ ] Verify: does injecting the wiki actually improve answers?

### Phase 2 — Automated wiki compilation (3-5 days)
- [ ] Ollama value gate + compiler prompts
- [ ] `compile_wiki_async()` as FastAPI BackgroundTask
- [ ] `_upsert_index()` keeping `_index.md` in sync
- [ ] Git auto-commit after each wiki update
- [ ] Version backup system (`.bak.md` files)
- [ ] `/admin/rebuild-index` endpoint for recovery
- [ ] Obsidian vault open on `./wiki/` for human inspection

### Phase 3 — Chat App frontend (2-3 days)
- [ ] Next.js chat UI with send/receive
- [ ] WikiSidebar showing active slug + preview
- [ ] Topic badge and context char count display
- [ ] Settings panel: model selector, wiki injection toggle

### Phase 4 — Semantic retrieval upgrade (1-2 weeks)
- [x] Pull `nomic-embed-text` via Ollama
- [x] `server/pipeline/embedder.py`: embed each article on write, store in sqlite-vec0 table
- [x] `server/pipeline/search_semantic.py`: vector cosine similarity search
- [x] `server/pipeline/query_search.py`: hybrid FTS5 + vector via Reciprocal Rank Fusion
- [x] `?mode=keyword|semantic|hybrid` query parameter on `GET /query`
- [x] Backfill script: `scripts/backfill_embeddings.py`
- [x] Tests: `tests/test_embedder.py`, `tests/test_semantic_search.py`, `tests/test_hybrid_search.py`

### Phase 5 — Knowledge graph overlay (advanced)
- [ ] Integrate **Graphiti** or **Zep** as graph memory layer
- [ ] Extract entities from Q+A (names, decisions, relationships)
- [ ] Store as graph nodes alongside wiki articles
- [ ] Use graph traversal to surface related context not in keyword index

---


## 10. Evaluation Metrics

| Metric | How to measure |
|--------|---------------|
| **Answer consistency** | Ask same question 3 turns apart — does answer reference earlier context? |
| **Token efficiency** | Compare tokens sent per turn: raw history vs. wiki summary |
| **Wiki fidelity** | Manually inspect articles — are facts accurately captured? |
| **Retrieval accuracy** | For 20 test questions, did the correct wiki slug get retrieved? |
| **Phase B latency** | Time from A_n returned to wiki file updated |
| **Over-compression rate** | How often does value gate SKIP when it should PROCESS? |

---


## 11. Key Gotchas to Watch

| Issue | Symptom | Fix |
|-------|---------|-----|
| Ollama BackgroundTask blocking | New chat feels slow | Queue one compilation at a time; add semaphore |
| Over-compression | Wiki article loses specific facts | Add "NEVER REMOVE existing content" to compiler prompt |
| Index drift | Wrong wiki retrieved | Run `/admin/rebuild-index`; add startup index validation |
| Context too large | Public LLM truncates | Hard-cap injection at 3,000 chars; truncate from the bottom |
| Wrong topic routing | Coding question retrieves business wiki | Tune keyword lists; add Ollama fallback classifier |
| Circular reinforcement | Wrong fact perpetuated | Add `/wiki/edit` UI so you can correct articles manually |
| Ollama cold start | First compilation takes 30s | Keep Ollama warm with a no-op request on delegator startup |
| M-series GPU | Ollama not using Metal | Ollama auto-detects Apple Metal — no config needed |

---


## 12. References

| Resource | Why relevant |
|----------|-------------|
| [Karpathy LLM-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Core wiki-as-memory philosophy; ingest/query/lint pattern |
| [Agent Skills](https://agentskills.io/home) | Keyword-triggered skill category taxonomy |
| [IBM M+ MemoryLLM](https://research.ibm.com/publications/m-extending-memoryllm-with-scalable-long-term-memory) | Scalable long-term memory theory |
| [Hindsight](https://hindsight.vectorize.io) | Reference implementation: Ollama + local memory engine |
| [LangChain ConversationSummaryMemory](https://python.langchain.com/docs/concepts/memory/) | Pre-built alternatives if custom becomes too complex |
| [LlamaIndex](https://www.llamaindex.ai) | Vector retrieval pipeline for Phase 4 |
| [Mem0 / Zep / Graphiti](https://www.getzep.com) | Drop-in graph memory for Phase 5 |
| [Ollama API docs](https://ollama.com) | Local model runtime reference |
| [ChromaDB](https://www.trychroma.com) | Local vector store for semantic retrieval |
