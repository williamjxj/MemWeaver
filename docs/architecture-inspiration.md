# mem-weaver Architecture Decision & Inspiration Doc

> **Purpose:** A comprehensive reference comparing approaches, technologies, and trade-offs for the mem-weaver project — so you can decide what to build, what to skip, and what to evolve.

---

## 1. Where You Are Today

### 1.1 What's Built (Actual Code)

| Component | Status | Notes |
|-----------|--------|-------|
| **FastAPI delegator** (`server/main.py`) | ✅ Implemented | `/ingest` (202 + async queue), `/query` (FTS5 BM25), `/health`, `/stats` |
| **SQLite + FTS5** (`server/db/`) | ✅ Implemented | `pages`, `qa_pairs`, `wiki_links` tables; FTS5 virtual tables with triggers |
| **Ollama client** (`server/ollama/client.py`) | ✅ Implemented | Async httpx wrapper with retry, `generate_json` + `generate_text` |
| **Ingest pipeline** (`server/pipeline/ingest_worker.py`) | ✅ Implemented | Queue → summarize → raw JSON → wiki page → SQLite upsert → index/log update |
| **Wiki graph** (`server/pipeline/wiki_graph.py`) | ✅ Implemented | `[[wikilink]]` extraction, inbound link counting |
| **Contradiction detection** (`server/pipeline/contradictions.py`) | ✅ Implemented | Compares new atoms against stored claims |
| **Prompt templates** (`server/pipeline/prompts.py`) | ✅ Implemented | Summarize, wiki page, contradiction check prompts |
| **Obsidian vault** (`wiki/`) | ✅ Working | `index.md`, `log.md`, `concepts/` pages, `LLM_WIKI_SCHEMA.md` |
| **Raw Q/A store** (`raw/qa/`) | ✅ Working | Immutable JSON per ingest |
| **Tests** (`tests/`) | ✅ Partial | `test_ingest_integration.py`, `test_fts_match_terms.py`, `test_contradictions.py`, etc. |
| **Frontend (Next.js)** | ❌ Not built | Planned in `second-brain-implementation-plan.md` but not started |
| **Semantic search (embeddings)** | ❌ Not built | Planned for Phase 4 in s2-plan, and Phase 4 in second-brain-plan |
| **Agent-Skills taxonomy** | ⚠️ Partial | Keyword taxonomy in `second-brain-implementation-plan.md` but not wired into code |

### 1.2 What's Planned (From Your Docs)

Your `second-brain-implementation-plan.md` (the "Nick Spisak inspired" plan) envisions:
- **Phase A (sync):** Classify → retrieve wiki summary → ask public LLM with summary injected
- **Phase B (async):** Ollama value gate → compile wiki → update `_index.md`
- **Frontend:** Next.js chat app with WikiSidebar
- **Multi-phase rollout:** Prototype → wiki compilation → chat app → semantic search → knowledge graph

Your `s2-claude-plan.md` (the "middleware delegator" plan) envisions:
- **Ingest:** Any LLM client → POST `/ingest` → Ollama distills → raw JSON + wiki + SQLite
- **Query:** GET `/query` → FTS5 BM25 → optional Ollama synthesis
- **No frontend planned** — this is a pure backend service

**Key observation:** You have TWO plans that partially overlap but differ in scope. The middleware plan is fully built; the second-brain plan is mostly a document.

---

## 2. The Ecosystem Landscape (2025–2026)

### 2.1 The Karpathy LLM-Wiki Pattern (The Foundation)

Published April 3, 2026 — crossed 5,000 stars in 2 weeks.

**Core insight:** Stop using RAG to re-derive answers from raw documents on every query. Instead, let the LLM **compile** raw sources into a structured, interlinked markdown wiki **once**, then query the compiled wiki.

**Three-layer architecture:**
```
Layer 1: raw/          — Immutable source material (articles, papers, transcripts)
Layer 2: wiki/          — LLM-maintained markdown (sources/, entities/, concepts/, synthesis/)
Layer 3: SCHEMA.md      — Agent config telling the LLM how to behave
```

**Operations:**
- **Ingest:** Read raw source → write summary page → update entity/concept pages → cross-link → update index + log
- **Query:** Read index → find relevant pages → synthesize answer with citations
- **Lint:** Health-check — broken links, orphans, contradictions, stale claims

**Scaling claim:** Works up to ~100–200 pages (~400K words). Beyond that, `index.md` overflows context → need hybrid search.

**What Karpathy explicitly says:**
> *"You rarely ever write or edit the wiki manually; it's the domain of the LLM."*
> *"The wiki is just a git repo of markdown files."*

### 2.2 The "Don't Use Karpathy's Second Brain" Counter-Argument

The YouTube video ([z02Y-1OvWSM](https://www.youtube.com/watch?v=z02Y-1OvWSM)) by **Nicholas Spisak** proposes an **Agent-Skills-powered alternative**:

| Aspect | Karpathy's Approach | Spisak's Approach |
|--------|-------------------|---------------------|
| **Scope** | Single giant vault for everything | **Domain-specific vaults** (one per project/topic) |
| **Trigger** | Manual `/ingest` command | **Agent Skills** — `/second-brain-ingest` auto-triggered by context |
| **Search** | `index.md` navigation (breaks at ~200 pages) | **qmd** (Tobi Lütke's hybrid BM25/vector search + LLM re-ranking) |
| **Structure** | Three folders: raw/, wiki/, output/ | Same three folders BUT with **skill-based onboarding wizard** |
| **Agent config** | Single `CLAUDE.md` | **Multi-agent config** — generates configs for Claude Code, Cursor, Gemini CLI, Codex, 40+ agents |
| **Maintenance** | Manual lint | **`/second-brain-lint`** skill — health-check as a command |
| **Query** | Manual "ask the wiki" | **`/second-brain-query`** skill — structured Q&A against wiki |

**Spisak's key additions:**
1. **Domain isolation:** Don't dump everything in one vault. Create separate vaults for "work-project", "personal-learning", "health-research". Each vault has its own wiki compiled independently.
2. **Agent Skills as the interface:** The wiki operations (ingest, query, lint) are packaged as **skills** that any AI agent can invoke — not just a one-off script.
3. **qmd for scale:** When the wiki outgrows `index.md` navigation, use `qmd` (Tobi Lütke's tool) — a local hybrid search engine with LLM re-ranking, shipped as both CLI and MCP server.
4. **Tiered model strategy** (from community discussions):
   - **Tier 1:** Cheap local LLM (Gemma 4B) for nightly ingest, draft generation, orphan detection
   - **Tier 2:** Expensive expert (Claude/Codex) for weekly review, synthesis, promotion
   - **Tier 3:** Human approval for promotions to long-term memory

### 2.3 The RAG vs Wiki Debate (Settled: They're Different Tools)

| Aspect | RAG | LLM Wiki | Hybrid (What You're Building) |
|--------|-----|-----------|----------------------|
| **Synthesis time** | Query time (re-derive) | Ingest time (pre-compile) | Both: compile wiki at ingest, retrieve from wiki at query |
| **Best scale** | Millions of docs, multi-domain | ~100-500 pages, personal/small-team | Start wiki, add RAG semantics later |
| **Infrastructure** | Vector DB + embedding model | Just markdown files + git | SQLite FTS5 (yours) + optional ChromaDB |
| **Token efficiency** | Retrieval batch varies | Very high (dense summaries) | Very high (wiki summaries as context) |
| **Correctness** | Raw source always available | Depends on compile quality | Dual-layer: raw JSON immutable, wiki is compiled view |
| **Multi-user** | Native (access control, permissions) | Poor (single-user markdown) | Not designed for multi-user |

**Consensus from 2026 ecosystem:** LLM Wiki and RAG solve *different* problems. Wiki = personal knowledge compilation. RAG = enterprise-scale retrieval. Your hybrid approach (wiki compilation + FTS5/semantic search) is the pragmatic middle ground.

### 2.4 Memory System Comparison (2026 State of the Art)

| System | Memory Type | Storage | Search | Local? | Notes |
|--------|-------------|---------|--------|---------|-------|
| **mem-weaver** (yours) | Wiki compilation + FTS5 | SQLite + Markdown | BM25 (FTS5) → future: embeddings | ✅ Yes | Dual-LLM: Ollama compiles, public LLM reasons |
| **Karpathy LLM Wiki** | Wiki compilation | Markdown + git | `index.md` lookup | ✅ Yes | The original pattern; scaling issues beyond ~200 pages |
| **Spisak second-brain** | Wiki + Agent Skills | Markdown + git | qmd (BM25 + vector + LLM re-rank) | ✅ Yes | Adds skill-based interface and domain isolation |
| **SuperLocalMemory V3.3** | Full cognitive taxonomy | SQLite + sqlite-vec | 7-channel (FTS5, vector, graph, temporal, spreading activation, consolidation, Hopfield) | ✅ Yes | Most complete local system; 17 packages, 215 modules, 60 MCP tools |
| **M2A (Multimodal Memory Agent)** | Dual-layer (raw + semantic) | SQLite | Tri-path (dense, BM25, cross-modal) + RRF | ✅ Yes | RawMessageStore + SemanticMemoryStore with evidence linking |
| **AdaSwitch** | Adaptive cloud-local | Cloud API + local model | Dynamic routing based on confidence | ☁️ Cloud + local | Routes complex steps to cloud, simple to local |
| **MemoryLLM / Zo Memory** | Semantic memory | Turso (sqld) + Ollama embeddings | Vector similarity | ✅ Yes | Focus on persistence across sessions |
| **Letta (ex-MemGPT)** | Function-call memory | Cloud (deprecated OSS) | Tool-based retrieval | ☁️ Cloud-only now | Pioneered LLM-managed memory via function calls |
| **Zep / Mem0** | Graph + vector | Cloud (Zep) / Cloud (Mem0) | Graph traversal + vector | ☁️ Cloud-only | Enterprise memory; Zep deprecated OSS |
| **NovaMem** | Vector store | Rust + Ollama embeddings | Vector similarity | ✅ Yes | Simple, local-first, auto-embedding |
| **hexit-recall** | Semantic + temporal | Ollama + nomic-embed-text | 6-channel + memory decay | ✅ Yes | Memory decay over time; self-improvement loop |
| **ChromaDB / Qdrant / Pinecone** | Pure vector DB | Local or cloud | Vector similarity | Both | Not a memory system by itself — just the storage layer |

---

## 3. Key Architectural Decisions for mem-weaver

### 3.1 Decision 1: What is the "Dual-LLM" Split?

Your current implementation (s2-claude-plan):
```
Public LLM (Claude/GPT) ← receives Q + wiki summary ← wiki/ + SQLite
                ↑
         Ollama (local) → compiles Q/A → wiki page + FTS5 index
```

The alternative (second-brain-plan):
```
Phase A (sync, 0ms overhead):
  User → Chat App → Delegator → retrieve Sk from wiki → Q + Sk → Public LLM → Answer → User

Phase B (async, background):
  Delegator → Ollama Value Gate → Ollama Compiler → Update wiki + index
```

**Recommendation:** Your current implementation already does Phase B well (async ingest). What's missing is **Phase A** — the chat app that *uses* the compiled wiki as context. The s2-plan has the better *retrieval* design (classify topic → retrieve relevant Sk → inject into public LLM). Consider merging both:

```
POST /chat (future endpoint):
  1. Classify question → topic + candidate slugs (Agent-Skills taxonomy)
  2. Retrieve best wiki summary (FTS5 + future semantic)
  3. Inject summary as priming context to public LLM
  4. Return answer + active slug to chat app
  5. Background: compile Q+A into wiki (existing /ingest pipeline)
```

### 3.2 Decision 2: Search — BM25, Vector, or Hybrid?

| Option | Pros | Cons | Recommendation |
|--------|------|------|-----------------|
| **FTS5 BM25 only** (current) | Zero infra, built into SQLite, fast, deterministic | No semantic understanding ("RAG" won't match "retrieval-augmented") | ✅ Good for v1 (100-500 pages) |
| **FTS5 + nomic-embed-text** | Semantic search finds related concepts; still local | Extra latency at ingest (embedding generation); Ollama must be running | ✅ Add in Phase 4, as originally planned |
| **qmd** (Tobi Lütke's tool) | Hybrid BM25 + vector + LLM re-ranking; used by Karpathy & Spisak | Another tool to install; Node.js dependency | ⚠️ Consider if FTS5 + embeddings isn't enough |
| **ChromaDB / Qdrant** | Proper vector DB; scales to millions | Infrastructure overhead; less "local-first" | ❌ Overkill for personal/small-team scale |

**Recommendation:** Stay with FTS5 for v1. Add `nomic-embed-text` embeddings in Phase 4 as originally planned. Use Reciprocal Rank Fusion (RRF) to merge BM25 + vector scores when you add semantics.

### 3.3 Decision 3: Wiki Structure — Flat or Hierarchical?

Your current `wiki/concepts/` is flat. The Spisak/Nick approach adds hierarchy:

```
wiki/
├── sources/           # One summary per ingested source
├── entities/          # People, orgs, products, tools
├── concepts/          # Ideas, frameworks, theories  ← your current location
├── synthesis/         # Comparisons, analyses, themes
├── index.md           # Master catalog
└── log.md             # Chronological operation record
```

**Recommendation:** Adopt the 4-folder structure. Your current `concepts/` works, but as the wiki grows, distinguishing between "what is X?" (concepts), "who is Y?" (entities), and "how do X and Y relate?" (synthesis) becomes valuable. The `sources/` folder maps 1:1 to your `raw/qa/` JSON files.

### 3.4 Decision 4: Agent-Skills Taxonomy — Keyword or LLM-Based?

Your `second-brain-implementation-plan.md` defines a fixed taxonomy:
```python
SKILL_TAXONOMY = {
    "coding":    { "keywords": ["python", "fastapi", "debug", ...], "wiki_paths": [...] },
    "design":    { "keywords": ["architecture", "system", "schema", ...], ... },
    "ml":        { "keywords": ["llm", "rag", "embedding", "ollama", ...], ... },
    "business":  { "keywords": ["deadline", "client", "budget", ...], ... },
    "general":   { "keywords": [], ... },
}
```

**Pros:** Fast (0ms), deterministic, debuggable.
**Cons:** Doesn't handle nuanced questions that span topics; fixed taxonomy can't adapt.

**Hybrid approach (recommended):**
1. **First pass:** Keyword matching against taxonomy (fast, handles 80% of cases)
2. **Fallback:** If keyword score = 0 → escalate to Ollama LLM classification (~1s)
3. **Future:** Dynamic topic discovery — let Ollama suggest new taxonomy entries when it sees repeated unseen keywords

### 3.5 Decision 5: Memory Lifecycle — Static or Decaying?

Current system: memories live forever (no decay).

From **LLM Wiki v2** and **SuperLocalMemory V3.3**, a growing consensus recommends:

| Tier | What | Decay Rate | Example |
|------|------|-------------|---------|
| **Working memory** | Recent observations, not yet processed | No decay | "User just asked about RAG" |
| **Episodic memory** | Session summaries, compressed from raw | Fast decay (days) | "Session 2026-04-21: discussed RAG patterns" |
| **Semantic memory** | Cross-session facts, consolidated | Slow decay (months) | "User prefers FastAPI over Django" |
| **Procedural memory** | Workflows and patterns | No decay (unless superseded) | "Ingest pipeline: Q/A → summarize → wiki" |

**Recommendation for v2:** Add a simple `last_accessed_at` + `access_count` to your `pages` table. Use these for ranking. Add a config option: "archive pages not accessed in N days." Don't delete — just deprioritize.

### 3.6 Decision 6: Contradiction Handling — Your Current Approach

Your `server/pipeline/contradictions.py` detects when new atoms contradict stored claims and appends a blockquote:
```markdown
> ⚠️ Contradiction noted:
> Stored: "Ollama uses port 11434"
> New: "Ollama uses port 8080"
```

**This is excellent.** It's the single most important correctness guardrail. Keep it. Consider adding:
- **Confidence scoring:** Each claim gets high/medium/low confidence
- **Human review queue:** `/stats` already shows orphan pages; add "contradiction count" to the response
- **Auto-archive low-confidence contradictions:** After N contradictory reports, move the page to `wiki/archive/` and create a fresh one

---

## 4. What to Build Next — Suggested Priorities

Based on your current state + ecosystem best practices:

### 4.1 Immediate (What's Missing from Current Build)

| Priority | Feature | Why |
|----------|---------|-----|
| **P0** | `GET /chat` endpoint (Phase A) | Your entire system compiles wiki but never *uses* it for context injection. This is the missing link. |
| **P0** | Agent-Skills taxonomy in code | `SKILL_TAXONOMY` exists in docs but not wired into `server/pipeline/` |
| **P1** | Chat app frontend (Next.js) | `second-brain-implementation-plan.md` has the code; just needs to be built |
| **P1** | WikiSidebar in frontend | Shows user which wiki article is being used as context |
| **P2** | `POST /lint` endpoint | Health-check: orphans, broken wikilinks, contradictions |

### 4.2 Phase 4 (As Originally Planned)

| Feature | Notes |
|---------|-------|
| **nomic-embed-text embeddings** | Add to Ollama pipeline; store as BLOB in SQLite (`sqlite-vec`) or separate table |
| **Hybrid search** | FTS5 BM25 + cosine similarity → Reciprocal Rank Fusion |
| **Multi-article retrieval** | Top-2 slugs, concatenated (with char cap) |
| **qmd as alternative** | Install as MCP server; compare results against your FTS5 + embedding approach |

### 4.3 Future (v2+)

| Feature | Inspiration | Notes |
|---------|--------------|-------|
| **Memory decay** | LLM Wiki v2, hexit-recall | `last_accessed_at` + exponential decay for ranking |
| **Tiered memory** | SuperLocalMemory V3.3 | Working → Episodic → Semantic → Procedural |
| **Graph traversal** | M2A, Mem0 | `wiki_links` table exists; add Steiner tree + spreading activation |
| **Cross-vault search** | Spisak second-brain | Domain-specific vaults; query across them |
| **MCP server** | SuperLocalMemory, sqlite-memory | Expose mem-weaver as MCP tools: `memory_search`, `memory_add`, `memory_maintain` |
| **Fine-tuning dataset** | Karpathy's gist | Wiki pages = high-quality training data for a small local model |

---

## 5. Tech Stack Decision Matrix

| Component | Current Choice | Alternative | Verdict |
|-----------|----------------|--------------|---------|
| **HTTP framework** | FastAPI + uvicorn | Flask, aiohttp | ✅ Keep FastAPI — async-native, Pydantic validation |
| **LLM (local)** | Ollama (llama3.2 / minimax-m2.7) | LM Studio, GPT4All | ✅ Keep Ollama — standard, well-supported |
| **Embedding model** | Not yet added | nomic-embed-text (planned), all-MiniLM, bge-small | ✅ nomic-embed-text — proven in ecosystem |
| **Primary storage** | SQLite + FTS5 | ChromaDB, Qdrant, PostgreSQL + pgvector | ✅ Keep SQLite — zero infra, FTS5 is built-in |
| **Wiki format** | Markdown + YAML frontmatter | Pure DB, JSON | ✅ Keep Markdown — Obsidian-compatible, git-native, human-readable |
| **Config** | pydantic-settings + .env | TOML, YAML | ✅ Keep pydantic-settings — type-safe, 12-factor |
| **Frontend** | Not yet built | Next.js (planned), Svelte, vanilla JS | ✅ Next.js 14 — matches your plan; consider if you even need a SPA (HTMX + FastAPI could work) |
| **Package manager** | pip + venv | uv (faster), poetry | ⚠️ Consider migrating to `uv` — your docs mention it but you're using venv |

---

## 6. Key Numbers from the Ecosystem

| Metric | Value | Source |
|--------|-------|--------|
| Karpathy's wiki scale | ~100 articles, ~400K words | Karpathy's gist |
| Wiki scaling limit (index.md) | ~100-200 pages | Community consensus |
| FTS5 BM25 works up to | ~1M records (responsive) | OpenClaw benchmarks |
| nomic-embed-text dimensions | 768 (compact) | Ollama docs |
| Ollama embedding latency | 100-300ms per text | BSWEN blog |
| Token savings vs raw history | Up to 95% | Atlan research |
| SuperLocalMemory channels | 7 parallel retrieval channels | V3.3 architecture |
| LLM Wiki v2 retention | Ebbinghaus exponential decay curve | rohitg00's gist |
| Cloud API cost (GPT-4o) | $5/1M input tokens (2026) | OpenAI pricing |
| Local Ollama cost | $0 (after model download) | — |

---

## 7. The "Don't Use Karpathy" Video — Summary for Decision

Since the background agent couldn't fetch the video transcript, here's what the ecosystem says about Spisak's counter-argument:

**What Spisak gets right:**
1. **Domain isolation:** One giant vault becomes unmanageable. Split by project/topic.
2. **Agent Skills interface:** Packaging wiki operations as skills makes them portable across AI agents (Claude Code, Cursor, Gemini CLI, etc.)
3. **qmd for scale:** Tobi Lütke's hybrid search tool is the pragmatic solution when `index.md` navigation breaks.

**Where Karpathy's approach is still superior:**
1. **Simplicity:** Three folders, one schema file, zero infrastructure. You can start in 10 minutes.
2. **Git-native:** Markdown files in git = perfect provenance, easy debugging, portable.
3. **Compilation philosophy:** "Memory shouldn't be retrieval — it should be synthesis" is the deeper insight.

**The synthesis for mem-weaver:**
Your project already implements Karpathy's compilation pattern (via the ingest pipeline) + adds database indexing (SQLite FTS5) that Karpathy explicitly didn't use. This puts you **ahead** of both approaches. What you're missing is:
1. The **Phase A chat endpoint** that *uses* the compiled wiki
2. The **Agent-Skills taxonomy** wired into code for topic routing
3. The **frontend** that shows users what context is being injected

---

## 8. Recommended Reading Order (If You Want to Dive Deeper)

1. 📖 **Karpathy's original gist** — [gist.github.com/karpathy/442a6bf555914893e9891c11519de94f](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — The foundation
2. 📖 **LLM Wiki v2** — [gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2) — Lifecycle, decay, hybrid search
3. 📖 **Spisak's second-brain repo** — [github.com/NicholasSpisak/second-brain](https://github.com/NicholasSpisak/second-brain) — Agent Skills packaging
4. 📖 **SuperLocalMemory V3.3 architecture** — [superlocalmemory.com/architecture](https://superlocalmemory.com/architecture) — Full cognitive taxonomy (for inspiration, not replication)
5. 📖 **M2A paper** — [arxiv.org/html/2602.07624v1](https://arxiv.org/html/2602.07624v1) — Dual-layer memory with evidence linking
6. 📖 **LLM Wiki vs RAG analysis** — [atlan.com/know/llm-wiki-vs-rag-knowledge-base](https://atlan.com/know/llm-wiki-vs-rag-knowledge-base) — When to use which

---

## 9. One-Page Decision Matrix for You

```
                    Karpathy    Spisak     Your Current    Recommended Next
                    (Gist)     (Skills)    (mem-weaver)   (mem-weaver v2)
                    ────────    ───────     ───────────    ───────────────
Compilation:        Ollama       Ollama      Ollama         ✅ Ollama
Storage:            Markdown     Markdown    SQLite+MD      ✅ SQLite+MD
Search:             index.md     qmd         FTS5 BM25      ✅ FTS5 + add embeddings
Topic routing:       Manual       Skills       Docs only      ✅ Wire taxonomy into code
Chat endpoint:       ❌           Planned      ❌              ✅ Build /chat
Frontend:           Obsidian     Obsidian     ❌              ✅ Next.js (planned)
Memory lifecycle:    Static       Tiered       Static          ⚠️ Add last_accessed + decay
Contradiction:       Lint         Lint         ✅ Implemented  ✅ Keep + enhance
Multi-vault:         ❌           ✅           ❌              ⚠️ Consider for v3
MCP server:          ❌           ❌           ❌              ⚠️ Future: expose as tools
Git provenance:       ✅           ✅           ✅ (raw JSON)   ✅ Keep immutable raw
```

---

*Document compiled: 2026-05-05*
*Sources: Karpathy gist (Apr 2026), Spisak second-brain (Apr 2026), LLM Wiki v2 (Apr 2026), SuperLocalMemory V3.3 (Mar 2026), M2A (Feb 2026), Atlan RAG vs Wiki (Apr 2026), mem-weaver codebase (Apr-May 2026)*
