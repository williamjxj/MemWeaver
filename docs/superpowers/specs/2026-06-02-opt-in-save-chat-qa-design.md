# Opt-in "Save to Memory" for Chat Q/A — Design Doc

**Date:** 2026-06-02
**Status:** Approved
**Stack:** FastAPI · Python 3.12 · Next.js 16 (App Router, Tailwind) · existing `/ingest` pipeline

---

## 1. Overview

Today every `/chat` turn is **automatically** ingested into `raw/qa/` and compiled into the wiki (the `/chat` route calls `enqueue_ingest` at end-of-stream). This change makes saving **opt-in per answer**: after an answer finishes streaming, the user can choose to save that Q/A pair to memory and optionally attach a freeform note.

### Key decisions (brainstorming outcomes)

| Decision | Choice |
|----------|--------|
| When the save decision is made | **After** the answer streams — per completed assistant message |
| Save control | A "Save to memory" checkbox; checking it reveals a note textarea + "Save" button |
| Default state | **Unchecked** — nothing is saved unless the user acts |
| Post-save | Show "Saved ✓" and **lock** the control (no re-save). On failure, stay actionable for retry. |
| Metadata | A freeform **`note`** — new optional field on `IngestPayload` + raw JSON, stored verbatim |
| Note scope | **raw/qa JSON only** — Ollama summarize/wiki-gen prompts unchanged |
| Wiring | **Reuse `POST /ingest`** (Approach A); add optional `note`; frontend calls backend directly like `streamChat` |
| Chat auto-save | **Removed** — `/chat` no longer enqueues an ingest at end-of-stream |

### Success criteria

1. After an answer completes, an unchecked "Save to memory" control appears under that assistant message.
2. Checking it reveals a note textarea + Save button; Save calls `POST /ingest` with `{question, answer, note, source:"chat"}`.
3. On success the control shows "Saved ✓" and locks; on failure it shows an inline error and remains usable.
4. The `note` is persisted verbatim in `raw/qa/<date>/<id>.json`.
5. `/chat` no longer auto-ingests; an unsaved turn produces no `raw/qa` record.

---

## 2. Behavior / Data Flow

```
User asks → /chat streams DeepSeek answer (NO auto-save)
Answer completes → "Save to memory" checkbox under that answer
  unchecked → no action (Q/A discarded when session clears)
  checked   → note textarea + "Save" button
    Save → POST /ingest {question, answer, note, source:"chat"}
         → enqueue_ingest → IngestJob(note) → background pipeline
           writes raw/qa/<date>/<id>.json (note included) + Ollama wiki compile
    success → "Saved ✓", control locks
    failure → inline error, control stays actionable (retry)
```

The `/chat` `done` event still returns the retrieved `wiki_slug`/`topic` (the *context* page used for the answer), which is independent of ingest and unaffected by removing auto-save.

---

## 3. Backend Changes

| File | Change |
|------|--------|
| `server/models/api.py` | `IngestPayload`: add `note: str \| None = None` |
| `server/main.py` `/ingest` | pass `note=payload.note` into `enqueue_ingest` |
| `server/services/memory_api.py` | `enqueue_ingest(...)`: add `note: str \| None = None` param; set on `IngestJob` |
| `server/pipeline/ingest_worker.py` | `IngestJob`: add `note: str \| None = None`; include `"note": job.note` in `raw_doc` JSON |
| `server/main.py` `/chat` | **Remove** the Phase-B `enqueue_ingest` block (auto-save after streaming) |

`note` is stored verbatim in the raw JSON only. SQLite schema, FTS tables, and Ollama prompt templates are untouched.

---

## 4. Frontend Changes

| File | Change |
|------|--------|
| `chat-app/lib/api.ts` | add `saveQa(question, answer, note): Promise<{ ok: boolean; ingest_id?: string }>` → `POST ${API_BASE}/ingest` |
| `chat-app/components/SaveToMemory.tsx` | **New** client component. Local state: `checked`, `note`, `status: "idle" \| "saving" \| "saved" \| "error"`. Checkbox reveals `<textarea>` + Save button. Calls `onSave(note)`. Renders "Saved ✓" + locks on success; inline error on failure. |
| `chat-app/components/ChatWindow.tsx` | Render `<SaveToMemory>` under each **completed** assistant message (excludes the message currently streaming). Provide the paired question (`messages[i-1].content`) + the answer, plus an `onSaveQa` handler. |
| `chat-app/app/page.tsx` | add `handleSaveQa(question, answer, note)` calling `saveQa`; pass `onSaveQa` down to `ChatWindow`. |

State is local per `SaveToMemory` instance (ephemeral, matches the lock-after-save rule). No cross-reload persistence — consistent with in-memory messages today.

---

## 5. Error Handling

- `saveQa` non-2xx or network error → component enters `error` state with a short inline message; Save remains pressable (does **not** lock on failure).
- Empty note is allowed (optional); save still proceeds.
- `/ingest` backend validation unchanged: requires non-empty `question`/`answer` (always satisfied here).

---

## 6. Testing

- Backend: extend an ingest test to assert `note` is persisted in the raw JSON; assert `/ingest` accepts payloads both with and without `note`.
- Backend: assert/smoke-check that `/chat` no longer enqueues an ingest on its own.
- Frontend: no test harness exists in `chat-app`; verify manually that checking the box reveals the textarea and Save calls `onSave`. (Add a test only if a harness is introduced.)

---

## 7. Notes / Out of Scope

- **Behavior change:** removing chat auto-save means turns are only captured when the user opts in. This is intentional per the request.
- `note` does not affect wiki generation or search ranking in this iteration (raw-only). Propagating it into the pipeline is a possible future follow-up.
