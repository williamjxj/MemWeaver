# ADR 003: SSE Streaming Pattern

## Context
Chat responses need to stream token-by-token so the UI feels responsive while the model is still generating output. The browser frontend is a Next.js app, the backend is FastAPI, and the system already uses a clean HTTP boundary between them. The stream also needs to carry status events such as completion and error conditions.

## Decision
Use Server-Sent Events for chat streaming from the FastAPI backend to the browser, and proxy that stream through the Next.js route handler. The backend emits structured SSE events such as `token`, `done`, and `error`, while the frontend forwards the raw event stream to the chat UI.

## Consequences
This gives the project a simple, one-way streaming model that works well for token delivery and progress notifications. It is easy to debug over plain HTTP and keeps the browser implementation straightforward. The tradeoff is that SSE is one-directional and less flexible than WebSockets for interactive bidirectional protocols or binary payloads.
