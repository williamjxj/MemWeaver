# Document Management

MemWeaver’s documentation should separate source drafts from canonical knowledge.

## Source Drafts

- `docs/v1/`, `docs/v2/`, and `docs/v3/` are the raw comparison set.
- Keep them read-only so they remain evidence of how the project was described over time.

## Canonical Layer

- Use `docs/adr/` for decisions with consequences.
- Use `docs/roadmap.md` for milestone-level direction.
- Use `docs/topics/` for stable topic summaries.

## Working Workflow

1. Compare similar drafts to find overlap, contradictions, and unique claims.
2. Extract stable facts and decisions into smaller notes.
3. Refine the notes into MemWeaver’s current terminology.
4. Merge only the strongest material into canonical docs.
5. Index the result from `docs/README.md` and the relevant folder README.

## Practical Rule

If a statement is still debated, leave it in a working plan or spec. If it is stable and useful for future work, move it into a topic note or ADR.