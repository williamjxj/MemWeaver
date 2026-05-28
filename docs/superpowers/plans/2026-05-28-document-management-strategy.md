# Plan: MemWeaver Document Management Strategy

**Issue**: `#2` - strategy for document management
**Scope**: `docs/` only
**Estimate**: 1-2 days for the first usable workflow

---

## Overview

MemWeaver already has multiple document streams that describe the same product from different angles:

- `docs/v1/` — earlier LLM-generated perspectives
- `docs/v2/` — revised perspectives with a stronger implementation focus
- `docs/v3/` — newer model outputs and follow-up drafts
- `docs/adr/` — durable architectural decisions
- `docs/roadmap.md` — milestone-level direction
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — working specs and execution plans

The goal is to turn these into a repeatable document pipeline that behaves like a lightweight LLM-wiki composition system: compare similar docs, extract durable ideas, refine conflicts, merge into canonical summaries, and index everything so later prompts can retrieve the best source quickly.

---

## Recommended Strategy

Use a 5-step lifecycle for every doc set:

1. **Compare** similar docs side by side to identify overlap, contradictions, and unique claims.
2. **Extract** stable facts, decisions, and open questions into smaller canonical notes.
3. **Refine** the extracted notes into a project-specific voice and structure.
4. **Merge** the best material into a canonical document for the topic.
5. **Index** all source and canonical docs with tags, backlinks, and a topic map.

This keeps the source drafts intact while gradually improving the docs that matter most.

---

## Doc Roles

### 1. Draft Sources

Keep `docs/v1/`, `docs/v2/`, and `docs/v3/` as immutable input collections.

Rules:

- Do not rewrite them in place.
- Treat them as evidence, not truth.
- Use them to compare model behavior and trace how the project thesis evolved.

### 2. Canonical Docs

Create or maintain a small canonical layer for durable knowledge:

- `docs/adr/` for decisions with consequences
- `docs/roadmap.md` for milestone sequencing
- `docs/README.md` for navigation and folder purpose
- topic-specific project notes under a dedicated `docs/topics/` or `docs/reference/` area if needed

### 3. Working Docs

Use `docs/superpowers/specs/` and `docs/superpowers/plans/` for short-lived execution artifacts.

Rules:

- Specs define the desired outcome and constraints.
- Plans define implementation order and files to touch.
- Once complete, link the final result back into the canonical layer.

---

## Suggested Folder Pattern

If the project keeps growing, add a small docs taxonomy:

- `docs/inbox/` — raw captures, notes, and imported drafts
- `docs/topics/` — canonical topic notes, one file per topic
- `docs/adr/` — architecture decisions
- `docs/superpowers/specs/` — implementation specs
- `docs/superpowers/plans/` — execution plans
- `docs/v1/`, `docs/v2/`, `docs/v3/` — source generations, read-only

If a new folder is introduced, add a short README in that folder so future contributors know how to use it.

---

## Workflow

### Phase 1: Compare

For a topic with multiple drafts, create a comparison note that answers:

- What is shared across all drafts?
- What changed between versions?
- What is still inconsistent or conflicting?
- Which version is most aligned with current product direction?

Output format:

- a short comparison matrix
- a list of disagreements
- a list of stable takeaways

### Phase 2: Extract

Pull the stable pieces into smaller notes:

- product goals
- user problems
- architectural decisions
- operational rules
- open questions

Each extracted note should have one clear job and link back to the source drafts.

### Phase 3: Refine

Rewrite extracted notes so they fit MemWeaver’s current terminology and repository structure.

Rules:

- prefer concrete project names over generic language
- use the same nouns as the codebase when possible
- trim repeated wording across notes
- keep unresolved questions visible

### Phase 4: Merge

Promote only the strongest material into canonical docs.

Merge criteria:

- the statement is stable across multiple sources, or
- the statement is a deliberate decision with an ADR, or
- the statement is needed as a user-facing guide

### Phase 5: Index

Maintain discovery aids so the docs remain searchable:

- a topic index for major project themes
- backlinks from specs/plans to canonical notes
- tags or frontmatter for source version, topic, and status
- a quick “start here” navigation page in `docs/README.md` or a dedicated index

---

## What to Canonicalize First

Start with the topics that recur across drafts and matter most to implementation:

- product thesis and scope
- chat + memory workflow
- ingest and retrieval pipeline
- document hierarchy and naming
- UI direction and dashboard layout
- MCP integration and IDE workflow

These are the highest-value areas for a normalized docs system.

---

## Document Metadata

Add lightweight frontmatter or header metadata where useful:

- `status`: draft | active | canonical | archived
- `source`: v1 | v2 | v3 | manual
- `topic`: short slug
- `owner`: optional maintainer or contributor
- `last-reviewed`: optional date

This makes it easier to filter and compare documents later.

---

## Review Rules

Before promoting a note to canonical:

- check whether it duplicates an ADR or roadmap entry
- ensure it uses project-specific language
- verify links to source drafts are present
- confirm the note adds navigation value, not just more prose

If a note is still uncertain, keep it in working docs instead of canonical docs.

---

## Implementation Order

### Step 1: Add a comparison note template

Create a reusable template for comparing related drafts.

### Step 2: Create a topic index

Add a compact index for the major topics in the repository.

### Step 3: Canonicalize one topic

Pick one recurring theme, compare the `v1`/`v2`/`v3` docs, and produce a canonical summary.

### Step 4: Add folder READMEs where needed

Document the purpose of `docs/topics/` or `docs/inbox/` if either folder is introduced.

### Step 5: Define maintenance cadence

Review the canonical docs whenever a major roadmap or product-direction change lands.

---

## Expected Outcome

After this strategy lands, MemWeaver should have:

- clearer separation between source drafts and canonical docs
- a repeatable way to compare and merge LLM-generated documents
- a better navigation layer for the docs folder
- a path toward llm-wiki-style composition without destroying source history

---

## Open Questions

- Should `docs/v1/`, `docs/v2/`, and `docs/v3/` stay strictly read-only forever?
- Do we want a `docs/topics/` layer, or should canonical notes live in existing folders only?
- Should metadata be frontmatter-based markdown or a separate index file?
- Which topic should be canonicalized first: product thesis, memory workflow, or UI strategy?
