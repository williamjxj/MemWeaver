# ADR 001: Dual-LLM Architecture

## Context
mem-weaver needs two different jobs to happen well: interactive answering and durable memory compilation. The answer path must feel immediate and useful to the user, while the memory path must distill Q/A into stable wiki pages, tags, and structured records. The system is also local-first, so the architecture should preserve privacy and keep the runtime simple enough to run on a single machine.

## Decision
Keep the conversational reasoning path and the memory-compilation path separate, even when they use the same underlying model provider. The chat path is optimized for user-facing responses, while the ingest path is optimized for background summarization, wiki writing, and index maintenance. This separation is enforced in the code by the chat endpoint, the shared `memory_api` layer, and the asynchronous ingest worker.

## Consequences
This keeps the user experience fast and makes the memory pipeline easier to evolve independently. It also lets the project swap or extend models later without redesigning the whole application. The tradeoff is extra orchestration complexity: there are now two execution paths to understand, monitor, and test.
