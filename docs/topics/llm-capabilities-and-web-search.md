# LLM Capabilities & Web Search

## Status: Verified Findings

### 1. DeepSeek V4 Flash — API does not support web search

The DeepSeek chat-completions API (`/v1/chat/completions`) is a pure text-in/text-out endpoint.
There is no `web_search`, `internet_search`, or equivalent parameter in the API surface.

| Capability | API | Web Chat (chat.deepseek.com) |
|---|---|---|
| Web search toggle | ❌ Not available | ✅ Has search toggle (UI feature only) |
| Function/tool calling | ✅ Supported | N/A |
| Streaming (SSE) | ✅ Supported | N/A |
| Training data cutoff | Static (mid-2025) | Same model, different UI |

The web search feature visible on chat.deepseek.com is a **website-specific UX feature**, not an
API capability. The same model behind both interfaces has the same knowledge limitations.

### 2. `frequency_penalty` — deprecated and silently ignored

DeepSeek's API docs (verified June 2026) explicitly list `frequency_penalty` as deprecated:

> **`frequency_penalty`**: This parameter is no longer supported and will not take effect.

The parameter is still accepted (no error), but **silently ignored**. This means our
`frequency_penalty: 0.4` in `server/services/deepseek_client.py` has no effect.
The identity-fix system prompt alone handles preamble suppression.

**Action**: Remove the `frequency_penalty` parameter from the API body to avoid misleading
reader intent. It's dead code.

### 3. Qwen2.5 7B (Ollama) — fully offline, no web access

The distill LLM runs locally via Ollama with no internet access. The ingest pipeline
(`server/pipeline/ingest_worker.py`) sends prompts to `http://127.0.0.1:11434/api/generate`
and only processes text the user provides via `/ingest`.

The model's modelfile shows it supports function calling in principle (the Ollama template
includes tool-call XML tags), but the **ingest pipeline does not use tools**. Every pipeline
step — summarization, wiki page writing, contradiction checking — is a single text-generation
call with no external tool invocation.

## What the Architecture IS Designed For

The system is a **knowledge management / memory layer**, not a general-purpose web search
assistant. The data flow makes this explicit:

```
User provides Q&A → qwen2.5 distills (offline) → wiki pages → SQLite + FTS + vectors
                                                              ↓
User asks question ← DeepSeek answers from context ← RAG retrieves relevant pages
```

### What it does well

- **Persistent memory**: Feed it once, it remembers. Q&A pairs are distilled into structured
  wiki pages with atoms, key claims, topics, and entities.
- **Domain-specific knowledge**: Internal docs, codebase patterns, project specs, team
  conventions — anything you teach it, it can answer from.
- **Offline-capable distill**: The qwen2.5 pipeline runs entirely locally. No internet
  required for the memory-writing path.
- **Deterministic retrieval**: FTS5 keyword search + sqlite-vec semantic search + hybrid
  RRF merge gives predictable, auditable results.

### What it cannot do

- Answer questions about recent events, news, or information nobody has ingested.
- Retrieve live API docs, package versions, or pricing.
- Search the web autonomously unless explicitly built as a tool.

## Options for Adding Web Search

If the assistant needs access to current information, there are viable paths.

### Option A: Function calling with a web search tool (recommended)

DeepSeek V4 Flash supports `tools` / function calling. The pattern:

1. Define a `web_search` function in the DeepSeek API call (in `deepseek_client.py`).
2. When the model decides the question needs current info, it returns a function call
   with the search query.
3. Your server executes the actual HTTP search (e.g., via a search API).
4. Feed results back as a `tool` role message and let the model answer from that context.

Relevant files to change:
- `server/services/deepseek_client.py` — add `tools` array to the API body
- `server/services/public_llm.py` — handle tool call responses in the stream
- `server/main.py` — wire up the web search execution (API key management, rate limits)

Considerations:
- Requires a search API key (SerpAPI, Tavily, Bing Search, etc.).
- Adds latency per tool call (model decides → server searches → model answers).
- DeepSeek does not charge extra for tool calls beyond token usage.

### Option B: Pre-ingest current information (zero code changes)

For specific, recurring information needs (e.g., latest version of a library, current
company policies), manually feed the data via `/ingest`:

```bash
# Ingest a current article or doc into the wiki
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the latest React version?", "answer": "React 19 is latest...", "source": "manual"}'
```

The ingest pipeline distills it into a wiki page, and future queries about React will
retrieve and surface that information.

Not suitable for:
- Rapidly changing information (stock prices, weather, news).
- Ad-hoc questions where you don't know what to pre-ingest.

### Option C: Keep the current design, document the constraint

The system is useful as-is for its intended use case (knowledge management). The limitation
is a design trade-off, not a bug. Document it so users understand what they're getting.

## Recommendation

For a **personal/knowledge management system**, Option C (accepting the constraint) + occasional
Option B (manual ingest of important docs) is sufficient. The system's value comes from
surfacing YOUR information, not the web's.

If the use case shifts toward a **general-purpose research assistant**, pursue Option A
(function calling with web search). The tool-calling infrastructure is already available
in DeepSeek's API — it's just not wired up yet.

## Related

- `server/services/deepseek_client.py` — current API body (remove `frequency_penalty`)
- `server/services/public_llm.py` — message construction (would add tool response handling)
- `server/pipeline/ingest_worker.py` — offline distill pipeline (no changes needed)
- [Two-tier LLM implementation plan](../plans/two-tier-llm.md) — original design rationale
- [Known Gaps](../known-gaps.md) — other missing capabilities
