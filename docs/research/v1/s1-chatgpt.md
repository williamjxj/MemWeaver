# LLM Memory Techniques – Retrieval vs. Summarization

Large language models (LLMs) are stateless by default: they have no built-in long-term memory.  Standard practice is **Retrieval-Augmented Generation (RAG)**, where an agent stores past data externally (e.g. in a vector database) and retrieves relevant pieces into the prompt.  For example, Amazon’s Bedrock documentation describes a typical RAG flow: the agent embeds the user query, searches a knowledge store, and **appends the retrieved context to the LLM prompt** before generating an answer【35†L142-L153】. This works well for factual queries, but every query starts “from scratch” on raw data.  

An alternative is the **“memory as synthesis” approach** (often called an LLM Wiki).  Here the LLM itself **periodically summarizes and consolidates** conversation content into a structured memory (like a knowledge base), rather than relying on raw text retrieval.  Andrej Karpathy’s “LLM Wiki” pattern is a leading example: instead of loading documents each time, the LLM **incrementally writes and maintains a persistent wiki of notes**.  When new information comes in, the LLM *updates or augments* those wiki pages (entity pages, concept summaries, etc.), so the knowledge “compiles” over time【27†L50-L59】【27†L75-L83】.  Karpathy argues that *“memory shouldn’t be retrieval”* – it should be synthesis by the LLM【27†L160-L164】.  In practice, this means compressing long chat histories into concise summaries or facts so that future answers can leverage a compact, up-to-date memory.  

AI-memory frameworks combine these ideas.  For example, tools like [LangChain](https://langchain.com/) and [LlamaIndex](https://llamaindex.ai/) support **memory chains** that either buffer recent exchanges or automatically summarize them for reuse.  Open-source systems like [Hindsight](https://hindsight.vectorize.io) or MemGPT/Letta extract entities and store facts in a graph.  These systems typically *“retain”* new facts (via LLM calls), *“recall”* relevant ones (via semantic search), and even *“reflect”* (multi-step reasoning) to answer complex queries【45†L84-L92】【40†L133-L138】.  For instance, Hindsight uses Ollama locally to parse conversation turns into a knowledge graph – extracting “Alice is a software engineer in Portland” from text and storing it as a fact【40†L109-L113】.  On a new query (“What languages does Alice prefer?”), it **retrieves** the relevant node and **reasons** over it to produce an answer. 

In summary, **modern agent memory** falls into two camps: (1) *Vector/RAG-based retrieval*, which appends external knowledge into the prompt at query time【35†L142-L153】, and (2) *LLM-driven summarization/wiki*, which incrementally builds a persistent memory of facts and summaries【27†L50-L59】【27†L160-L164】.  The user’s idea – feeding Q&A pairs into a local LLM to produce a wiki-like summary and using that summary as the next prompt’s memory – follows the second pattern.  

# Official LLM Memory Features

Most public LLM APIs do **not** natively maintain long-term memory.  For example, OpenAI’s **API** has no memory toggle – any persistence must be engineered externally【15†L18-L24】.  (OpenAI’s *ChatGPT UI* recently added a personal memory feature, but it is not exposed via the API【15†L18-L24】【22†L59-L68】.)  Anthropic’s Claude offers a **Memory Tool**: in its developer platform, Claude can *call a memory API* to read/write files locally.  The Claude docs explain that it “stores information across conversations through a memory file directory,” letting the model create/read/update/delete files client-side【8†L214-L223】【8†L249-L258】.  In effect, Claude can “bolt on” a custom retrieval system by writing summaries or facts to a file system, then pulling relevant pieces into context when needed【8†L219-L228】.  

Meta’s Llama (via their Llama API) likewise has no special memory feature beyond the usual context window.  Typically one would combine Llama with a separate RAG or memory system (e.g. LlamaIndex or a graph database).  Ollama (which runs local open models) also has **no built-in memory** – it simply serves an LLM locally (via `http://localhost:11434/api`).  However, Ollama fully supports standard chat APIs, so you can implement memory by calling Ollama to summarize or answer with memory included.  In fact, Ollama provides *Anthropic-compatible* endpoints, so existing tools (like Claude Code) can “speak” to a local LLM as if it were Claude【39†L95-L103】.  

# Hybrid Public LLM + Local Memory Architecture

The user’s proposed design is a **hybrid memory pipeline** using two LLMs: a high-quality cloud model (e.g. OpenAI or Claude) for answers, and a local model (via Ollama) for memory compression.  The flow is:  

- **User Query → Public LLM Answer:** The app sends Q₁ to the cloud LLM API. It returns answer A₁.  
- **Local Summarization:** The app takes *Q₁ and A₁* (or a recent batch of Q/A) as input to the local LLM (via Ollama).  The local model generates a concise summary or knowledge-entry **S₁** that captures the key facts or outcome of that exchange (e.g. in a wiki style).  This memory S₁ is saved in a local store and categorized (by topic or context) for later retrieval.  
- **Next Query with Memory:** On the next user query Q₂, the app retrieves the relevant memory S₁ (or multiple past summaries) from the store. It then constructs the prompt to the public LLM: for example, a system message or preceding content that embeds S₁ along with Q₂.  The public LLM generates answer A₂ *using S₁ as context*.  

Repeating this loop, the system “remembers” by continually summarizing recent interactions into knowledge snippets and feeding them back as needed.  This follows Karpathy’s insight: build and maintain a small AI “wiki” of user info rather than shoving raw chat history each time【27†L50-L59】.  In effect, the local LLM is the *memory manager* and the public LLM is the *QA engine*.  Since S₁ is shorter than full logs, each prompt to the public LLM stays compact, avoiding context bloat. 

**Diagram (conceptual):** 

```
User: Q₁ → [Public LLM] → Answer A₁
             ↓
   [Local LLM (Ollama) summarizes (Q₁,A₁) → S₁ saved in memory by topic]
             
User: Q₂ + S₁ → [Public LLM] → Answer A₂
             ↓
   [Local LLM summarizes (Q₂,A₂) → S₂ saved, etc.]
             
... and so on ...
```

This is similar to the “Long Chat Memory” patterns in tools like LangChain or MemGPT/Letta. In particular, Hindsight demonstrates a local memory engine combined with Ollama: the local model extracts and stores facts, then queries (`recall`) and multi-step reasons (`reflect`) over them to answer【45†L38-L41】【45†L84-L92】.  In Hindsight’s terms, our system does a simpler “retain” (summarize Q/A) and then uses that retained memory as prompt context.  

# Feasibility, Trade-offs and Evaluation

This hybrid approach **can work**, but has trade-offs:  

- **Accuracy vs. Memory Quality:** Summarization relies on the local model’s quality. A good summarizer will capture the essential facts (like “User is Alice, a software engineer, likes jellyfish”). If it omits details, the public LLM may not fully “remember” them. Conversely, writing verbose memory could blow up context. The summary must balance brevity with fidelity. It’s effectively creating a semantic index.  

- **Context Window / Cost Savings:** Compared to re-sending full chat logs, feeding a concise summary means fewer tokens in the public LLM’s prompt. This saves API costs and fits longer histories into limited context windows. It also aligns with how ChatGPT’s memory feature works (it stores user preferences in short form rather than full transcripts).  

- **Latency and Compute:** Using two LLM calls per turn doubles latency: one to the cloud LLM and one to the local model. Local LLMs (e.g. on Ollama) may be **slower** than cloud APIs, especially if large (e.g. a 20B model can take seconds per response). However, they incur *no direct per-token cost*. One must budget sufficient RAM/VRAM for the local model (the Hindsight guide notes a 20B model needs ~16GB GPU)【45†L113-L121】.  

- **Privacy:** Local summarization keeps raw conversation data on-device. But if the memory summary S is then sent into the public API, that user info still leaves the machine. Full privacy would require a local LLM answering all queries, but at present public models often give higher-quality answers. The hybrid model is a compromise.  

- **Complexity:** This system is more complex than a single-LM pipeline. You must build or adopt a memory store (could be as simple as files or a database). You also need logic to select which memory entries to include per query (topic matching or retrieval). Without clever retrieval, you might feed irrelevant memory or miss needed context. For example, if the user asks about “coffee shop slogans” but the stored memory is about jellyfish, the system must decide whether to include it. (One could use semantic search on memory or simple tags.)  

- **Scalability and Maintenance:** Over time the memory store grows. You’ll need to manage, prune, or revise memories. Karpathy’s wiki pattern includes “lint” steps to merge or discard outdated facts【27†L123-L132】. Without that, the memory could accumulate contradictions or obsolete info.  

In summary, the idea is **reasonable and feasible**, but it’s essentially building a custom memory/RAG system. It echoes known architectures (e.g. MemGPT, Mem0/Zep) but uses summarization instead of purely vector lookups【27†L50-L59】【43†L478-L484】. Off-the-shelf memory frameworks exist (LangChain’s memory modules, Mem0, Zep/Graphiti, Hindsight, etc.), but they often assume control over the entire agent. Here, since the user still relies on a generic public LLM API, they have to hack memory on top.

# Implementation Steps and Examples

1. **Choose Models and Setup:**  
   - **Public LLM:** Sign up for an API (OpenAI, Anthropic, etc.). For example, use OpenAI’s GPT-4, gpt-4o, or Anthropic’s Claude. Ensure you have an API key.  
   - **Local LLM via Ollama:** Install Ollama on your Mac. Pull a reasonably capable model (e.g. `gpt-oss:20b` or a “Gemma” model). Ollama runs a server on `localhost:11434` with an Anthropic/OpenAI-compatible API【37†L82-L90】【39†L95-L103】.  
   - **Memory Store:** Decide where to save summaries (local files, SQLite/JSON DB, or a simple vector store). For quick proof-of-concept, even a folder of text files or a local database works.

2. **First Query Flow (No Memory):** Send user’s first question Q₁ to the public API. For ChatGPT:  
   ```json
   POST https://api.openai.com/v1/chat/completions
   {
     "model": "gpt-4o",
     "messages": [
       {"role": "system", "content": "You are a helpful assistant."},
       {"role": "user", "content": "Explain Newton's Laws."}
     ]
   }
   ```  
   Save the user message `Q₁` and the assistant reply `A₁`.

3. **Generate Summary with Local Ollama:** Take the chat (Q₁, A₁) and prompt the local model to summarize the key points. For example, using Ollama’s Anthropic-compatible API in Python:  
   ```python
   import anthropic
   client = anthropic.Anthropic(base_url="http://localhost:11434", api_key="ollama")
   # Summarize conversation into memory format
   summary = client.messages.create(
       model="gpt-oss:20b",
       max_tokens=200,
       messages=[
           {"role": "system", "content": "Summarize the conversation facts concisely."},
           {"role": "user", "content": "User: Explains Newton's laws; Assistant: answers with definitions and examples."}
       ]
   )
   S1 = summary.content[0].text
   print("Memory entry S1:", S1)
   ```  
   (The actual prompt should include the real Q₁ and A₁ text.) The local LLM might produce something like: “Newton’s Laws: 1) Inertia; 2) F=ma; 3) Action-reaction, with examples. User asked for explanation.” Save `S1` (for instance as `memory/physics_newton_laws.txt`).  

4. **Store and Categorize Memory:** Organize summaries by topic or date. You could tag them (“Physics”) or place them in subfolders. This is akin to “Agent Skills” modules grouping capabilities【6†L90-L100】. For retrieval simplicity, you might keep a JSON index mapping keywords to file names, or do a quick search over all summaries for relevance.  

5. **Subsequent Query with Memory:** On next question Q₂, first decide which memories apply. For simplicity, you might include all recent summaries, or use a vector search of Q₂ against stored S₁, S₂, etc. Suppose Q₂ is related to Newtonian physics; you retrieve “Newton’s Laws” memory S₁. Then construct the prompt for the public LLM, e.g.:  
   ```json
   POST https://api.openai.com/v1/chat/completions
   {
     "model": "gpt-4o",
     "messages": [
       {"role": "system", "content": "Recall facts: Newton’s Laws: 1) ...; 2) ...; 3) ..."},
       {"role": "user", "content": "How do these apply to a car crash scenario?"}
     ]
   }
   ```  
   Here, we’ve turned `S1` into a system message or an initial assistant message that the LLM can use as context. The public LLM then returns A₂, ideally building on the remembered facts.  

6. **Iterate:** After Q₂→A₂, repeat the summarization step on (Q₂,A₂) to produce S₂, append to memory, and continue. Over time you build a chain of memory entries. You may periodically refine old summaries or prune irrelevant ones.  

**Example Payloads:**  

- *Local Ollama Summarization (Anthropic API format):*【39†L99-L108】  
  ```python
  client = anthropic.Anthropic(base_url='http://localhost:11434', api_key='ollama')
  response = client.messages.create(
      model='qwen3-coder',  # or another Ollama model
      messages=[{'role': 'user', 'content': "Summarize: " + conversation_text}]
  )
  summary = response['messages'][0]['content']
  ```  
- *Public LLM with Memory (OpenAI format):*  
  ```json
  {
    "model": "gpt-4o",
    "messages": [
      {"role": "system", "content": "Memory: Alice is a software engineer who likes Python and jazz music."},
      {"role": "user", "content": "What gift should I buy Alice for her birthday?"}
    ]
  }
  ```  
  (The assistant would generate an answer using the memory about Alice’s preferences.)  

Each step requires carefully prompting the LLMs. For example, instruct the local model clearly that it’s summarizing or extracting facts, and instruct the public model that the provided memory content is context, not a user query. Ensure the role tags (“system”, “assistant”, “user”) are used consistently so the LLM understands which parts are memory versus new question.  

# Trade-offs and Practical Considerations

- **Token Budget:** Summaries Sᵢ must fit in the context budget along with Qₙ. Using summaries reduces tokens vs. raw chat logs, but you still must manage growth. In practice, you might limit memory to the *most relevant* 2–3 entries.  
- **Latency:** Each memory operation adds an LLM call. Ollama can be CPU/GPU-limited. Hindsight notes that the *first* local model call is slow to load (~seconds) and later calls are queued if concurrency >1【40†L177-L184】. Plan for this delay (e.g. async calls or caching).  
- **Cost:** Using a public API (GPT-4/Claude) incurs cost per token. By feeding summaries instead of full history, you save tokens. Local Ollama uses free open models (no API fees), but still consumes electricity.  
- **Privacy:** Storing and summarizing sensitive data locally is safer, but once you include it in an API prompt, it’s shared. If true privacy is needed, you might run a local model end-to-end (at the expense of accuracy).  

# Conclusion

In short, the proposed dual-LLM memory scheme is **plausible and aligns with modern AI memory research**.  It essentially builds a user-specific knowledge base via summarization and uses it to augment a chat model’s context.  This is analogous to Karpathy’s LLM Wiki idea【27†L50-L59】, Hindsight’s local memory engine【45†L38-L41】【45†L84-L92】, and other hybrid memory systems【26†L73-L82】【26†L90-L99】.  Implementation involves managing two APIs (public and local), designing prompts for summarization, and storing the results.  With careful tuning of prompts and memory retrieval logic, the system can yield more coherent, context-aware answers than a stateless chat alone. 

**Sources:** We drew on official docs (Anthropic’s Memory tool【8†L214-L223】, Ollama’s API guide【37†L82-L90】【39†L99-L108】), recent AI memory research (Karpathy’s LLM Wiki【27†L50-L59】【27†L160-L164】, RAG architecture【35†L142-L153】, AI memory frameworks【26†L73-L82】【26†L90-L99】【43†L478-L484】【43†L514-L522】), and the Hindsight tutorial on local memory【45†L38-L41】【45†L84-L92】. These confirm that hybrid memory augmentation is an active area of development and suggest best practices for building such a system.