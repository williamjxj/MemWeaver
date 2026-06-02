# Collect → Distill → Canonical File → Ingest
## 多LLM知识提炼与上下文工程完全指南

> **Core assertion**: Raw multi-LLM output is noise. Value emerges only after distillation into
> assertion-dense canonical files that coding tools (Cursor, Claude Code, OpenCode, VSCode) can
> consume as structured context. The pipeline has four discrete stages; skipping any one breaks
> the chain.

---

## Stage Map

```
Claude ──┐
ChatGPT ─┤   RAW       FILTER      DISTILL      CANONICAL       INGEST
Gemini ──┼──► dump ──► signal ──► synthesis ──► .md files ──► tool context
Grok ────┤   (noise)   (keep)     (your job)   (structure)    (searchable)
Perplexity┘
```

**Time budget per topic**: Collect 20 min · Filter 10 min · Distill 30 min · Canonical 15 min · Ingest 5 min = ~80 min for a durable knowledge artifact.

---

## Stage 1 — Collect (收集)

### What to ask and where

Ask the **same 3–5 seed questions** across all LLMs, not free-form browsing:

```
Seed question template:
  "In [TOPIC], what are the (a) core concepts, (b) common failure modes,
   (c) best current tools, (d) non-obvious tradeoffs, and (e) your top
   recommended approach? Be specific — give names, versions, commands."
```

| LLM | Strength | Use for |
|-----|----------|---------|
| Claude (Sonnet/Opus) | Deep reasoning, architecture | System design, tradeoffs, code review |
| ChatGPT (GPT-4o) | Breadth, up-to-date tools | Tool discovery, ecosystem survey |
| Gemini 2.0 Flash | Code generation, Google stack | Implementation details, Python/Go |
| Grok | Real-time web, X/Twitter signal | Emerging tools, community opinion |
| Perplexity | Cited sources, research | Fact-checking, papers, docs links |

### Capture format — do this immediately

Never paste into a doc later from memory. Use this structure per LLM per question:

```markdown
## [LLM name] | [YYYY-MM-DD] | Q: [seed question short form]

[paste raw response here, no editing]

### My annotation:
- KEEP: [bullet key claims worth keeping]
- SKIP: [what's redundant/wrong/generic]
- VERIFY: [claims needing fact-check]
```

Store in `raw/[topic]/[llm]-[date].md` — this is your immutable source layer (mirrors MemWeaver's `raw/qa/` design).

### Anti-patterns to avoid at collection stage

- ❌ Asking different questions to each LLM → incomparable outputs
- ❌ Pasting everything into one giant doc immediately → can't trace provenance
- ❌ Collecting more than 5 LLMs per topic → diminishing returns after 3
- ❌ Collecting without annotation → you forget why you kept it within 48h

---

## Stage 2 — Filter / Signal Extraction (过滤)

### The 5-signal test (apply to every paragraph)

Score each block 0–5. Keep only blocks scoring 3+.

| Signal | Question | Example pass | Example fail |
|--------|----------|-------------|-------------|
| **Specificity** | Does it name exact tools/versions/numbers? | "Use `sqlite-vec` 0.1.3 for vector search in SQLite" | "Vector databases are useful" |
| **Actionability** | Can I act on this today? | "`pip install mcp-server-fastapi`" | "MCP is an emerging standard" |
| **Non-obviousness** | Would I know this without the LLM? | "FTS5 BM25 scores are negative; more negative = better" | "SQLite supports full-text search" |
| **Consensus** | Do 2+ LLMs agree? | All 3 say "use hybrid search not pure semantic" | One LLM says something unusual |
| **Contradiction** | Does it conflict with other LLMs? | Flag for deeper research, high value | Silently ignore conflicts |

### Conflict detection matrix

When LLMs disagree, that's the most valuable signal — it marks genuine tradeoffs:

```
Claude says:  "Use Ollama nomic-embed-text for local embeddings"
ChatGPT says: "Use OpenAI text-embedding-3-small, it's better quality"
Gemini says:  "Use sentence-transformers/all-MiniLM-L6-v2 for offline"

→ KEEP ALL THREE with context:
  - nomic-embed-text: best for fully local/private setups
  - text-embedding-3-small: best quality if API cost is acceptable
  - all-MiniLM-L6-v2: best for offline/air-gapped
```

Conflicts don't cancel each other — they define the **decision space** for your canonical file.

---

## Stage 3 — Distill / Synthesis (提炼) ← the hardest stage

### The synthesis algorithm

1. **Cluster** all KEEP bullets by concept (not by LLM source)
2. **Merge duplicates** — if 3 LLMs say the same thing, write it once
3. **Resolve conflicts** → state the tradeoff, not a winner
4. **Add structure** → "Facts", "Tradeoffs", "Decision criteria", "Gotchas"
5. **Apply the retrieval test**: *if an AI reads only this section, can it answer correctly?*

### Distillation prompt (use Claude/ChatGPT to help)

After collecting raw notes, feed this to an LLM:

```
System: You are a technical editor. Distill the following multi-LLM research
into a dense, assertion-rich wiki article. Rules:
- Every sentence must state a specific fact (name, number, command, path)
- No hedging: "generally", "often", "can be" → delete or make specific
- Where sources conflict, state the tradeoff explicitly
- Output in markdown with sections: Facts, Implementation, Tradeoffs, Gotchas
- Target: 200–400 lines, ≥4 assertions per 100 tokens
- NO narrative filler. Start every bullet with the fact, not "It is worth noting"

Input (multi-LLM raw notes):
[paste your annotated raw/ files here]
```

This is **meta-distillation**: using an LLM to distill LLM outputs. Takes ~5 minutes, produces ~80% of the final canonical file. You do the last 20% (add your own experience, remove errors).

### Quality gate before proceeding

The distilled content must pass:

- [ ] Zero sentences with: "it is important", "many ways", "generally speaking", "see X for details"
- [ ] Every tool/library named with version or command
- [ ] Every tradeoff has ≥2 named options with explicit criteria for choosing
- [ ] Gotchas section exists with ≥3 non-obvious failure modes
- [ ] Readable without any of the raw LLM outputs (self-contained)

---

## Stage 4 — Canonical File(s) (统一标准文件)

### File type selection matrix

| File | Consumed by | Format | Scope |
|------|------------|--------|-------|
| `CLAUDE.md` | Claude Code (auto-loaded at project root) | Markdown | Project-wide context |
| `AGENTS.md` | OpenCode, Windsurf, Codex CLI | Markdown | Agent behavior rules |
| `.cursorrules` | Cursor IDE | Markdown | Cursor-specific conventions |
| `.github/copilot-instructions.md` | GitHub Copilot | Markdown | Copilot context |
| `llms.txt` | Any LLM via HTTP | Markdown | Public API/docs |
| `wiki/[slug].md` | MemWeaver RAG, manual @-reference | Markdown+frontmatter | Topic deep-dive |
| `_context.md` | Any LLM (paste into context window) | Concatenated markdown | Session injection |

**Rule**: One topic → one `wiki/[slug].md` → referenced from `CLAUDE.md` + `AGENTS.md`.
Never duplicate content across files — cross-reference instead.

### Canonical file anatomy (wiki article)

```markdown
---
title: "RAG Chunking Strategies"
slug: rag-chunking
tags: [rag, embeddings, retrieval, llm]
aliases: [chunking, text-splitting]
related: [vector-search, hybrid-search, embedding-models]
updated: 2026-05-23
sources: [claude-2026-05-20, chatgpt-2026-05-21, gemini-2026-05-21]
---

# RAG Chunking Strategies

> **One-liner**: Chunk size 256–512 tokens with 10–20% overlap outperforms
> larger chunks for Q&A; use semantic chunking for narrative text.

## Facts

- Fixed-size chunking: split every N tokens, overlap M tokens (M = 0.1–0.2 × N)
- Optimal N for Q&A tasks: 256–512 tokens (LlamaIndex benchmark 2024)
- Semantic chunking: split at sentence/paragraph boundaries using sentence-transformers
- Recursive character splitting (LangChain `RecursiveCharacterTextSplitter`): best default
- Chunk overlap prevents context loss at boundaries; 50-token overlap is standard
- Small-to-big retrieval: embed small chunks, retrieve surrounding large chunk for LLM

## Implementation

\`\`\`python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]  # priority order
)
chunks = splitter.split_text(document)
\`\`\`

## Tradeoffs

| Approach | Best for | Weakness |
|----------|----------|---------|
| Fixed-size | Uniform docs, PDFs | Splits mid-sentence |
| Semantic | Narrative text, articles | Slower, variable chunk sizes |
| Recursive | General purpose (default) | Needs tuning for code |
| Small-to-big | Dense technical docs | More complex pipeline |

## Gotchas

- Chunk size 1024+ tokens degrades retrieval precision for Q&A tasks (too much noise per chunk)
- Overlap > 25% of chunk size causes duplicate retrieval, inflates context window usage
- Code blocks should never be split mid-block; add `"\`\`\`"` to separator list
- Metadata (source, page number, section) must be attached to EVERY chunk at ingest time
- Re-chunking after index is built requires full re-embed; design chunk size upfront

## Related

- [[vector-search]] — embedding model choice affects chunking strategy
- [[hybrid-search]] — FTS5 search operates on raw text, not chunks
```

### CLAUDE.md structure for a topic-heavy project

```markdown
# [Project Name]

## What this is
[2-3 sentences. Stack, problem, users.]

## Active knowledge base
This project uses wiki/ as its canonical knowledge store.
Load these files for context on specific topics:

| Topic | File | When to load |
|-------|------|-------------|
| RAG pipeline | @wiki/rag-chunking.md | Any retrieval/embedding work |
| MCP integration | @wiki/mcp-server-design.md | Any MCP tool work |
| LLM selection | @wiki/llm-model-selection.md | Any model choice |

## Architecture
[stack diagram]

## Conventions
[specific enforceable rules]

## Gotchas
[top 5 non-obvious project-specific issues]
```

---

## Stage 5 — Ingest (导入)

### Integration per coding tool

**Claude Code** (auto-loads `CLAUDE.md` from project root):
```bash
# Place at project root — loaded automatically every session
cp wiki/_context.md CLAUDE.md
# Or reference individual wiki files inline during session:
# "Read @wiki/rag-chunking.md then implement chunking for the ingest pipeline"
```

**Cursor** (`.cursorrules` + manual `@` references):
```
# .cursorrules
This project has a wiki/ directory with canonical knowledge articles.
Before implementing any feature, check if a relevant wiki article exists:
- RAG work → read wiki/rag-chunking.md
- MCP work → read wiki/mcp-server-design.md
Use @wiki/[slug].md in chat to inject specific articles.
```

**OpenCode / Codex CLI** (`AGENTS.md` at project root):
```markdown
# AGENTS.md
## Knowledge base
Wiki articles in wiki/ are canonical. Read the relevant article before
implementing. Use Read tool on wiki/[slug].md.

## Tool use rules
- Always Read wiki article before Write on related feature
- bash: run tests after every implementation change
```

**VSCode Copilot** (`.github/copilot-instructions.md`):
```markdown
This project maintains a wiki/ directory. When answering questions about
RAG, chunking, embeddings, or MCP — check wiki/ first. Key files:
wiki/rag-chunking.md, wiki/mcp-server-design.md, wiki/_context.md (full bundle).
```

**MemWeaver** (your existing system — use `/ingest` endpoint):
```bash
# Ingest a canonical wiki article into MemWeaver
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the optimal RAG chunking strategy?",
    "answer": "'$(cat wiki/rag-chunking.md | head -50)'",
    "source": "canonical-wiki"
  }'

# Or batch ingest all wiki files:
for f in wiki/*.md; do
  slug=$(basename $f .md)
  curl -X POST http://localhost:8000/ingest \
    -d "{\"question\": \"$slug\", \"answer\": \"$(cat $f)\", \"source\": \"wiki\"}"
done
```

---

## Tools & Automation (工具与自动化)

### Tier 1 — No-code / Low-code (use today)

| Tool | Role | Free? |
|------|------|-------|
| **NotebookLM** (Google) | Upload 5 LLM outputs → generate synthesis, podcast, FAQ | Yes |
| **Obsidian** + Dataview | Local vault for canonical .md files, graph view of links | Free core |
| **Obsidian Smart Connections** | Semantic search across your wiki vault | Plugin, free |
| **Mem.ai** | Auto-organizes notes, AI search across all captures | Paid |
| **Reflect.app** | Networked notes with LLM assist | Paid |
| **Roam Research** | Graph-based knowledge, block references | Paid |

**Best no-code stack**: Obsidian (vault = `wiki/`) + Smart Connections plugin + Git sync.
Your canonical `.md` files live in Obsidian AND are the same files Cursor/Claude Code reads.

### Tier 2 — Agent-assisted (1–2 hours setup)

**Claude.ai Projects** (built-in):
```
1. Create a Project named "[Topic] Research"
2. Upload all raw LLM outputs as files
3. System prompt: "You are a knowledge distiller. When asked, synthesize
   these files into a dense wiki article. Apply: specificity, no filler,
   state conflicts as tradeoffs."
4. Chat: "Distill these into a canonical wiki article on [topic]"
5. Copy output → wiki/[slug].md
```

**Cursor Agent** (use your own editor):
```
1. Create raw/[topic]/ with all LLM outputs as .md files
2. Open Cursor, use Composer/Agent mode
3. Prompt: "Read all files in raw/[topic]/, distill into wiki/[topic].md
   following the template in wiki/_template.md"
4. Review + commit
```

**OpenCode one-shot**:
```bash
opencode "Read raw/rag-research/*.md, distill into wiki/rag-chunking.md
following the format in wiki/_template.md. Apply quality gate: no filler,
all tools named with versions, gotchas section required."
```

### Tier 3 — MCP Servers (best integration)

**Existing MCPs that directly serve this workflow**:

| MCP Server | Function | Install |
|-----------|---------|--------|
| `@modelcontextprotocol/server-filesystem` | Read/write wiki/*.md files | `npx @modelcontextprotocol/server-filesystem wiki/` |
| `@modelcontextprotocol/server-memory` | Persistent key-value memory across sessions | npm |
| `mcp-obsidian` | Read/write Obsidian vault | pip or npm |
| `mcp-sqlite` | Query MemWeaver's SQLite directly | `uvx mcp-server-sqlite --db-path db/wiki.db` |
| MemWeaver (add MCP) | Your own wiki as MCP tool | see below |

**Add MCP to MemWeaver** (minimal implementation):

```python
# server/mcp.py — add to existing FastAPI app
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MemWeaver")

@mcp.tool()
async def search_wiki(query: str, mode: str = "hybrid") -> str:
    """Search the MemWeaver wiki knowledge base."""
    results = await wiki_retriever.search(query, mode=mode)
    return "\n\n".join(r.content for r in results[:3])

@mcp.tool()
async def ingest_knowledge(question: str, answer: str, source: str) -> str:
    """Add Q&A pair to MemWeaver wiki."""
    ingest_id = await pipeline.ingest(question, answer, source)
    return f"Ingested as {ingest_id}"

# Mount alongside FastAPI:
# app.mount("/mcp", mcp.streamable_http_app())
```

```json
// .cursor/mcp.json or claude_desktop_config.json
{
  "mcpServers": {
    "memweaver": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

After this, Cursor/Claude Code can call `search_wiki("RAG chunking")` mid-session without you doing anything.

### Tier 4 — ETL Pipeline (for scale / automation)

**Do you need a custom ETL pipeline?**

| Scenario | Recommendation |
|----------|---------------|
| <20 topics, manual collection | No — use Tier 1 or 2 |
| 20–100 topics, team of 1–3 | Light scripts (see below) |
| 100+ topics, or team | Yes — build the pipeline |
| Continuous ingestion from chats | Yes — MemWeaver already does this |

**Minimal ETL script** (Python, ~80 lines):

```python
#!/usr/bin/env python3
"""
distill_pipeline.py
Collect raw LLM outputs → call Claude API → write canonical wiki article
"""
import anthropic, pathlib, sys

DISTILL_PROMPT = """
You are a technical knowledge distiller.
Read the multi-LLM research below and produce a canonical wiki article.
Rules:
- Frontmatter: title, slug, tags, related, updated, sources
- Sections: Facts (bullets), Implementation (code), Tradeoffs (table), Gotchas
- Every sentence must state a specific fact (name, number, command, path)
- No filler. No hedging. Conflicts become explicit tradeoffs.
- Target 200-400 lines.
"""

def distill(topic: str, raw_dir: pathlib.Path, out_dir: pathlib.Path):
    # Gather all raw LLM outputs for this topic
    raw_content = "\n\n---\n\n".join(
        f"## Source: {f.name}\n{f.read_text()}"
        for f in sorted(raw_dir.glob("*.md"))
    )
    
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"{DISTILL_PROMPT}\n\nTopic: {topic}\n\n{raw_content}"
        }]
    )
    
    slug = topic.lower().replace(" ", "-")
    out_file = out_dir / f"{slug}.md"
    out_file.write_text(msg.content[0].text)
    print(f"✓ Written: {out_file} ({len(msg.content[0].text)} chars)")

if __name__ == "__main__":
    topic = sys.argv[1]  # e.g. "RAG chunking strategies"
    distill(
        topic=topic,
        raw_dir=pathlib.Path(f"raw/{topic.lower().replace(' ', '-')}"),
        out_dir=pathlib.Path("wiki")
    )
```

```bash
# Usage:
python distill_pipeline.py "RAG chunking strategies"
python distill_pipeline.py "MCP server design"
# Output: wiki/rag-chunking-strategies.md, wiki/mcp-server-design.md
```

**Full ETL pipeline** (when you need automation):

```
raw/[topic]/          ← LLM outputs (your manual input or scraped)
    ↓ distill_pipeline.py (Claude API)
wiki/[slug].md        ← canonical articles
    ↓ bundle_wiki.py
wiki/_context.md      ← full bundle for context injection
    ↓ sync_tools.py
CLAUDE.md             ← project context (updated with wiki links)
AGENTS.md             ← agent rules (updated with wiki links)
.cursorrules          ← cursor rules (updated with wiki links)
    ↓ ingest_wiki.sh
MemWeaver /ingest     ← searchable via /query and MCP
```

**Agent skill** (wrap in MemWeaver's skill system):

```python
# scripts/distill_skill.py
# Called by MemWeaver background worker when a chat exchange is high-value
class DistillSkill:
    trigger = "when response contains ≥3 technical claims about a new topic"
    
    async def run(self, question: str, answer: str, topic: str):
        # 1. Write to raw/
        # 2. Call distill_pipeline.py
        # 3. POST wiki article to /ingest
        # 4. Update CLAUDE.md with new wiki reference
        pass
```

---

## Decision Framework (use this)

```
Is the topic complex / long-lived / used across projects?
├── YES → full pipeline: Collect → Filter → Distill → Canonical → Ingest
│         Time: 80 min first time, 20 min updates
│         Tools: Obsidian + distill_pipeline.py + MemWeaver MCP
└── NO  → skip distillation
          Copy the single best LLM answer directly into CLAUDE.md as a bullet
          Time: 2 min

Do you have ≥5 topics to distill?
├── YES → automate with distill_pipeline.py + ingest script
└── NO  → manual Obsidian + Claude.ai Project

Do you want IDE-native access without copy-paste?
├── YES → add MCP server to MemWeaver (4-hour task)
└── NO  → @-reference wiki/*.md files manually in Cursor/Claude Code
```

---

## The Anti-Pattern Hall of Fame (what breaks this)

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| Collecting from 7+ LLMs | Signal-to-noise collapses, consensus becomes noise | Max 3–4 LLMs per topic |
| No annotation at collection time | Can't trace which LLM said what, why you kept it | Annotate immediately with KEEP/SKIP/VERIFY |
| One giant `notes.md` with everything | Unretrieval-able, context window overload | One file per topic, ≤500 lines |
| Re-asking LLMs instead of checking wiki | Reinvents the wheel every session | Search MemWeaver first: `GET /query?q=...` |
| Updating canonical file without versioning | Lose history, can't debug model regression | Git commit every wiki update with `git log --oneline wiki/` |
| Distilling to prose narrative | LLMs read bullets faster, lower hallucination rate | Facts section = bullets only |
| Skipping the Gotchas section | Most valuable section, always omitted | It's required; if you can't list 3 gotchas, you don't know the topic yet |

---

## Quick-Start (80-minute first run)

```bash
# 1. Ask the same 5 seed questions to Claude, ChatGPT, Gemini (20 min)
mkdir -p raw/my-topic

# 2. Save annotated outputs (10 min)
# raw/my-topic/claude-2026-05-23.md
# raw/my-topic/chatgpt-2026-05-23.md
# raw/my-topic/gemini-2026-05-23.md

# 3. Run distillation (5 min compute, 25 min review)
python scripts/distill_pipeline.py "my topic"
# → wiki/my-topic.md (review, edit, approve)

# 4. Add reference to CLAUDE.md (2 min)
echo "| My topic | @wiki/my-topic.md | Any my-topic work |" >> CLAUDE.md

# 5. Ingest into MemWeaver (3 min)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d @<(jq -n --rawfile ans wiki/my-topic.md \
    '{question:"my topic overview",answer:$ans,source:"canonical"}')

# Done. Next session: Claude Code reads CLAUDE.md → loads wiki → no re-research.
```

---

## Summary Assertions

- **The distillation step is irreplaceable** — LLMs cannot reliably distill their own outputs in real-time; you must do it once and store it.
- **Canonical files are not notes** — they are structured artifacts optimized for AI retrieval, not human reading.
- **MCP is the highest-leverage automation** — one 4-hour implementation gives every future coding session access to your entire wiki without copy-paste.
- **MemWeaver already implements this pipeline** — your gap is only Stage 4 (MCP exposure) and Stage 1 (structured collection from external LLMs).
- **Git is your version control for knowledge** — treat `wiki/` like `src/`, with commits, diffs, and blame.
- **Distillation is a skill that compounds** — your first distillation takes 30 min, your 20th takes 10 min, and your wiki becomes the moat.
