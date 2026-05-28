# ADR 004: Canonicalize Document Management Around Source Drafts and Topic Notes

## Context
The repository already contains multiple document streams that repeat the same product ideas from different LLM passes: `docs/v1/`, `docs/v2/`, and `docs/v3/`. These drafts are useful as evidence, but they are harder to navigate when the repository also needs stable guidance for roadmap, architecture, and implementation work.

## Decision
Treat `docs/v1/`, `docs/v2/`, and `docs/v3/` as read-only source material. Promote stable, project-specific knowledge into a small canonical layer made of ADRs, roadmap entries, and topic notes under `docs/topics/`.

## Consequences
This preserves the history of how the project evolved while giving contributors a clearer place to look for the current answer. It also makes it easier to compare drafts, extract durable ideas, and avoid rewriting the same content in multiple versions. The tradeoff is that the team must be disciplined about promoting only stable material into the canonical layer and leaving uncertain or experimental content in working docs.