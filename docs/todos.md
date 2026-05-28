## Miss

- memory taxonomy: missing explicit episodic / semantic / procedural separation; the industry has standardized on this for good reason.
- graph reasoning: wikilink graph is flat; lacks entity nodes, typed edges, and relationship queries.
- production scalability 
- Ecosystem / Framework fit: No MCP server
- No temporal reasoning — facts aren't timestamped with validity windows
- sqlite-vec constraints ?


## Improvement Recommendation

- Add a knowledge graph layer (entity + relations)
- Add temporal validity to stored facts
- Expose as an MCP server
- Implement the 3-tier memory taxonomy (episodic, sementic-'distilled wiki facts', procedural)
- Add multi-tenant memory scoping
- Evolve(改进) wiki pages with A-Mem style linking
- Automate embedding generation (remove backfill script)
- Add explicit memory compression/summarization layer

## Docs reorganization (2026-05-28)

Completed:

- Moved supporting architecture artifacts to `docs/references/`:
	- `architecture-diagram.html` -> `docs/references/architecture-diagram.html`
	- `architecture-inspiration.md` -> `docs/references/architecture-inspiration.md`
- Kept ADRs in `docs/adr/` (decision records only).
- Added `docs/README.md` as a docs home that links `adr/`, `references/`, `roadmap.md`, and `CHANGELOG.md`.
- Updated `README.md` and `docs/PROJECT_BRIEF.md` to reference the changelog, roadmap, and ADRs.
- Patched `docs/05-13.md` and Obsidian workspace metadata to point to `docs/references/`.

Next:

- Sweep remaining docs (`v2/`, `v3/`) to normalize terminology ("Next.js chat frontend shipped", "MCP server"), update inter-doc links, and ensure no broken relative paths remain.

