# Memory Management in LLM Chat Applications

Large language models (LLMs) have limited *context windows*, so a common solution is to use external memory to preserve important information across turns.  Instead of blindly including the full chat history in every prompt (which quickly hits token limits), state-of-the-art systems compress or retrieve past knowledge.  For example, **conversation summarization** compresses old turns into a short summary, and **retrieval-augmented memory** fetches relevant facts from a database.  In practice, hybrid architectures mix both: keep recent exchanges in context and store older insights externally【10†L768-L771】【14†L413-L422】.  Andrej Karpathy’s “LLM Wiki” idea is a prominent example – the agent builds a persistent, interlinked wiki of knowledge by reading sources (or past chats) and writing summaries, rather than re-deriving answers from scratch each time【4†L103-L112】【1†L259-L267】.  

**Types of LLM memory:** LLMs can maintain *short-term memory* (the current session context) and *long-term memory* (persistent knowledge across sessions)【8†L639-L642】【10†L768-L771】.  Tools like LangChain exemplify this: a `ConversationBufferMemory` simply keeps all previous messages, while `ConversationSummaryMemory` compresses older turns into a narrative【10†L698-L707】.  These approaches trade off completeness vs. efficiency: full buffers preserve detail but may overflow the context window, whereas summaries fit more content at the cost of some fidelity【14†L381-L388】【10†L698-L707】.  In addition, vector-based memory stores (embedding databases) can hold facts or past dialogues for semantic retrieval when needed【14†L398-L407】【10†L849-L858】.  Altogether, an effective memory design often uses the context window for recent info and an external store for the rest【10†L768-L771】【14†L413-L422】.  

- *Conversation Buffer Memory:* Keep all recent messages (works for short chats)【10†L698-L702】.  
- *Summary Memory:* Periodically ask an LLM to write a summary of past dialogue, then feed that into new prompts.  E.g. LangChain’s `ConversationSummaryMemory` compresses older turns into a concise recap【10†L698-L707】.  
- *Sliding Window:* Only keep the last *N* messages (a moving window) to limit context size【10†L698-L702】.  
- *Hybrid (Summary + Buffer):* Use a summary for older turns and keep the latest turns verbatim for maximum context (LangChain’s `ConversationSummaryBufferMemory`)【10†L701-L709】.  

## Modern Chatbot Memory: Official Features

Leading LLM chat systems are beginning to include built-in memory features.  **Anthropic’s Claude** can summarize and remember chat content.  For example, Claude automatically generates a “memory summary” of your past conversations (updated daily) and uses that synthesis as context for new chats【16†L123-L128】.  Users can also ask Claude to search or recall specific details from prior sessions via retrieval-based “chat search” (under the hood it uses RAG tool calls)【16†L51-L60】【16†L123-L128】.  Similarly, **OpenAI’s ChatGPT** now offers a memory feature: it automatically picks up personal preferences and facts from your chats and “remembers” them across sessions【17†L101-L109】.  For instance, if you tell ChatGPT your favorite game or pet’s name in one chat, it will recall that detail later.  OpenAI emphasizes that you can explicitly review or delete such memories in the ChatGPT settings.  These developments show a trend: LLM chat services are moving toward combined short/long-term memory, albeit currently as closed systems for end users【17†L101-L109】【17†L103-L112】.

By contrast, **public LLM APIs (GPT, Claude API, etc.) are stateless** by default – they do not automatically store memory between calls.  Any multi-turn consistency must be handled by the developer via prompt engineering.  In practice, this means your app must manage its own memory buffer.  Typical strategies include appending the entire Q/A history to each new prompt (up to the token limit) or using external stores.  The user’s proposed approach (two LLMs with summaries) is exactly a custom memory system on top of a stateless API.

## Two-LLM Memory Workflow

The user suggests a **two-LLM pipeline**: a public LLM (e.g. ChatGPT/Claude) handles the live Q&A, while a local LLM (via Ollama) compresses conversation history into a “wiki” memory that is fed back into future queries.  The basic loop is:

1. **User asks Q1 → Public LLM answers A1.** The app receives Q1/A1 and passes them (or just Q1) to the local LLM.
2. **Local LLM generates summary S1.** Based on Q1 (and possibly A1), the local LLM writes a concise wiki-style summary of what was discussed.
3. **Memory store updates:** Save S1 (and any relevant metadata, topics, etc.) in a persistent memory repository (could be text files or a database).
4. **Next user question Q2:** Instead of replaying raw Q1/A1, the app retrieves S1 from memory and includes it in the prompt to the public LLM: “Given this summary S1 of past talk, answer Q2.”
5. **Public LLM produces A2** with S1+Q2 as context.
6. **Repeat:** After each answer, update memory. For example, combine previous summary(s) with the new Q/A (Q2/A2) via the local LLM to produce an updated summary S2 for future use.

This approach is similar to the “LLM Wiki” concept【4†L103-L112】 and has been demonstrated in practice.  For example, the *MemoryLLM* project uses a local Gemma3 model via Ollama to implement exactly this pattern: it keeps recent turns in a sliding window for context, uses a vector DB for long-term facts, and asynchronously extracts key facts from conversation (e.g. “user’s name is Alex”) to store as memory【19†L273-L281】【19†L338-L343】.  In that system, the local LLM automatically tags and summarizes information from the chat, and the assistant can retrieve it later.  Likewise, Karpathy’s LLM-wiki suggests the LLM itself should compile conversation (and document) content into a personal wiki【4†L103-L112】.  

### Benefits and trade-offs

- **Pros:** Summarizing chat history means the public LLM sees only a distilled version of prior discussion.  This preserves important context (goals, facts, preferences) without exhausting the token budget【10†L698-L707】【14†L381-L388】.  It also encourages consistency: the memory summary can resolve contradictions and keep facts straight over time【4†L103-L112】.  Using two LLMs can leverage the strengths of each (e.g. a fast local model for summarization, a powerful cloud model for content generation).  It also decouples memory updates from answering, allowing asynchronous processing or human oversight if needed (similar to the “ingest” and “query” steps in the wiki architecture【4†L113-L122】).
- **Cons:** There is extra cost and latency. Every new batch of turns requires another LLM call to summarize (and possibly vector-storage overhead)【14†L381-L388】. A local LLM (like one on Ollama) may produce less accurate or more verbose summaries than a larger cloud model. Summarization inherently loses some detail (“fidelity loss”), so if the summary misses key information, the next answers may be less informed【14†L381-L388】.  Also, managing memory topics or categories adds complexity: one must decide *when* to update or split summaries. Finally, combining two LLM calls means slower responses (public API latency plus local compute), which may or may not be acceptable depending on the app’s requirements.

Overall, this two-LLM design is **reasonable and feasible**.  It follows patterns recommended in the literature – e.g. using `ConversationSummaryBufferMemory` in LangChain【10†L701-L709】 or a dual short/long-term memory system【14†L413-L422】【10†L768-L771】.  Many teams already implement similar workflows (see [MemoryLLM](19) or custom RAG setups).  The key is careful engineering to ensure summaries stay relevant and context windows aren’t overloaded.

## System Architecture and Data Flow

A concrete architecture might look like this:

- **User Interface (App):** Captures user questions and displays LLM answers.
- **Public LLM API Client:** Sends (memory + current question) to the cloud LLM (Anthropic/ChatGPT) and receives an answer.
- **Local LLM Summarizer:** Runs on Ollama with a local model (e.g. Gemma3). Receives recent conversation data (e.g. the latest Q/A or Qs alone) and returns a summary or extracted facts.
- **Memory Store:** A persistent store (could be markdown files, a database, or a vector store) holding summaries or indexed chunks. Optionally organize by topic groups or tags.
- **Retrieval/Trigger Mechanism:** Decides which memory pieces to include for each new question. For example, it could use keyword matching or vector similarity on the question to fetch relevant summary segments. Alternatively, the local LLM can be prompted to “activate” certain knowledge entries as needed (similar to agent tools).

**Data flow steps:**

1. **Chat:** User sends Q1 → App sends Q1 + any memory context (initially none) to Public LLM → Public LLM returns A1.
2. **Memory Update:** App packages Q1 (and possibly A1) as a “source” and sends it to the Local LLM Summarizer. The summarizer generates new content S1 (e.g. “User’s goal: X; key details: Y, Z”).
3. **Store Memory:** Insert S1 into the Memory Store. Tag or categorize it (e.g. under topics mentioned in Q1). Optionally maintain an index or wiki structure for easy lookup.
4. **Next Query:** User asks Q2. Before calling the Public LLM, retrieve relevant memory. This could be simply retrieving all S1 (if small) or searching which parts of S1 relate to Q2. For example, the local LLM might be prompted: “Based on the summary S1, list relevant facts about [topic in Q2]”.
5. **Compose Prompt:** Combine retrieved memory snippet M (from S1) with Q2 in the prompt. For example: `System: “Remember these facts from earlier chat: [M]”. User: “Now answer: [Q2]”.`
6. **Chat:** Send the combined prompt to Public LLM → receive A2.
7. **Iterate:** After A2, send the new exchange (Q2/A2) to the Summarizer to update memory (producing S2). The Memory Store now contains S1 and S2 (or an updated combined summary). Repeat for Q3, Q4, etc.

This can be visualized as:

```
User Q1 → [Public LLM] → A1
             ↓
        (Store Q1/A1 in temp chat buffer)
             ↓
        [Local LLM] → summary S1
             ↓
      (Memory Store ← S1)
             ↓
User Q2 + (retrieve relevant from S1) → [Public LLM] → A2
             ↓
    (Store Q2/A2) → [Local LLM] → summary S2
             ↓
      (Memory Store ← S2)
             ↓
User Q3 + (retrieve from S2) → ...
```

Key components:
- **Context window management:** The Public LLM sees only a small context (the summary M and the new question) rather than the full dialogue history. This keeps token usage low and cost predictable【10†L698-L707】.
- **Memory indexing:** For efficiency, the Memory Store might be organized (e.g. vector index or tagged wiki). This allows retrieving just the relevant part of S1 for each new question, rather than feeding the entire summary every time.
- **Human / Audit loop (optional):** As in Karpathy’s approach【4†L113-L122】, one could review or correct memory summaries periodically (or use a second model to “lint” the memory for contradictions). This adds robustness at the expense of complexity.

## Implementation Steps

To build this system, one might proceed as follows:

1. **Set up the Public LLM API:** Sign up for Anthropic/ChatGPT API, get API keys. Use the official Python or REST client. For example, with OpenAI:
   ```python
   import openai
   openai.api_key = "YOUR_OPENAI_KEY"
   response = openai.ChatCompletion.create(
       model="gpt-4", 
       messages=[{"role":"user","content":"Hello"}]
   )
   answer = response.choices[0].message["content"]
   ```
2. **Run a local LLM via Ollama:** Install Ollama and pull a model (e.g. `gemma3:4b-qat`). Start the Ollama server (`ollama serve`). You can then query it via HTTP. For example, using the Ollama API:
   ```bash
   curl http://localhost:11434/api/chat \
        -d '{"model":"gemma3", "messages":[{"role":"user","content":"Summarize: Q1 and A1 here."}]}'
   ```
   In Python, you could use `requests.post` to the same endpoint【21†L95-L101】【23†L85-L93】.
3. **Memory Store:** Choose storage. Simple options: a folder of Markdown files (one per conversation or topic), or a lightweight database. For retrieval, you might also store embeddings. If using a vector store (e.g. Chroma, Pinecone), you would embed either the raw Q/A or the summary text. Alternatively, a structured wiki (like Obsidian files) could work as Karpathy suggests【4†L103-L112】.
4. **Update Memory:** After each new Q/A, invoke the local LLM to process the recent text. For example:
   ```python
   recent_text = f"User: {Q2}\nAssistant: {A2}"
   summary_prompt = f"Summarize the above exchange as concise facts or key points."
   summ_resp = requests.post("http://localhost:11434/api/chat",
                             json={"model":"gemma3",
                                   "messages":[{"role":"system","content":summary_prompt},
                                               {"role":"assistant","content":recent_text}]
                                  })
   summary = summ_resp.json()["message"]["content"]
   ```
   Append `summary` to your memory store.
5. **Retrieval Logic:** Before each new question, decide which memory to include. Options:
   - **Full summary:** If memory is short, just include it wholesale.
   - **Selective recall:** Use keywords from the question to query your memory store. For example, if memory is in a database, do a semantic search for similar entries. Or prompt the local LLM: “Based on these notes: [S1], what is relevant to [Q3]?”
   - **Topic tagging:** If you categorized memory by topic, pick the matching topic pages.
6. **Combine and Query:** Merge the retrieved memory snippet `M` with the new question `Q_new`. A simple prompt format is:
   ```
   System: "Recall this from earlier conversation: [M]"
   User: "[Q_new]"
   ```
   Then send that to the public LLM as the next turn.  
7. **Loop and Refine:** Continue this pipeline. Monitor how well the memory assists. You may need to adjust:
   - How often you summarize (every turn vs. every few turns).
   - The level of detail in the summary prompt (one-liner vs. bullet list).
   - Whether to include answers or just questions in the summary. (In practice, include answer content or facts extracted from it for completeness.)
8. **Agent Skills (optional):** If you break memory into “skills” or categories, you could define specific prompts or even modular agents to handle each topic (like a skill for “User profile”, one for “Project details”, etc.). Each skill could have its own memory summaries.

Throughout, pay attention to prompt design. Providing the local LLM with a clear instruction (e.g. “Write a wiki-style summary of the user’s background and main requests”) will help create useful memory entries. Likewise, for the public LLM, a system prompt like “Use the following memory to answer: …” can clarify its task.

## Evaluation Metrics

To assess this memory system, consider:

- **Answer Quality:** Does including the memory actually improve correctness and consistency?  One could design test dialogues where the answer to a later question depends on earlier info. Compare the two-LLM setup versus a baseline (no memory or naive history) using human judgment or automated metrics (e.g. answer accuracy, informativeness).
- **Memory Fidelity:** Check if the summaries accurately capture key facts. You might periodically inspect or have the LLM “audit” memory for errors or contradictions (Karpathy’s approach【4†L199-L208】).
- **Context Efficiency:** Measure token usage. Summaries should reduce the number of tokens needed in the prompt versus sending raw history. Track API token cost with and without summarization.
- **Latency:** Record response times. Two LLM calls add latency; measure end-to-end delays. Possibly overlap summarization computation with user’s next input to hide some delay.
- **Scaling:** As conversation grows, check that retrieval still finds relevant info. In a wiki approach, the indexed summary should handle hundreds of turns without blowing past model limits【4†L103-L112】.
- **User Satisfaction:** Ultimately, gauge if the chat feels more coherent. If this is a product feature, user feedback (or proxies like session length) can indicate value.

## Conclusion

In summary, using two LLMs to manage memory is a valid and increasingly common strategy. It combines *retrieval/summarization memory* with live chat. The local model compiles past Q&As into a distilled memory that the public LLM can leverage for future answers. This “LLM wiki” approach【4†L103-L112】 is supported by recent research and industry practice: it mitigates context limits and yields more consistent, knowledgeable bots. The trade-offs include added complexity, cost of extra LLM calls, and potential information loss in summaries【14†L381-L388】【10†L698-L707】. In practice, careful engineering (e.g. when to summarize, how to retrieve) will make this system effective. If implemented properly—using the Ollama API for local inference【21†L95-L101】 and robust memory storage—the user’s plan should indeed be feasible and can lead to a more intelligent and memory-aware chatbot.

**Sources:** Current memory strategies are discussed in Karpathy’s LLM-wiki concept【4†L103-L112】, LangChain documentation【10†L698-L707】, OpenAI and Anthropic memory docs【16†L123-L128】【17†L101-L109】, and modern blog analyses of LLM memory architectures【14†L381-L388】【10†L768-L771】. The *MemoryLLM* project demonstrates a similar hybrid approach using Ollama for memory extraction【19†L273-L281】【19†L338-L343】. These sources inform the feasibility and design of the two-LLM memory workflow described above.