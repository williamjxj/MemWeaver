# Known Gaps & Improvement Recommendations

## Missing Capabilities

- **Memory taxonomy**: No explicit episodic / semantic / procedural separation — the industry has standardized on this.
- **Graph reasoning**: Wikilink graph is flat; lacks entity nodes, typed edges, and relationship queries.
- **Temporal reasoning**: Facts aren't timestamped with validity windows.
- **Multi-tenant scoping**: Single-user only.
- **sqlite-vec constraints**: Unknown capacity/performance ceiling for large-scale vector search.

## Improvement Recommendations

- Add a knowledge graph layer (entity + relations)
- Add temporal validity to stored facts
- Implement the 3-tier memory taxonomy (episodic, semantic — distilled wiki facts, procedural)
- Add multi-tenant memory scoping
- Evolve wiki pages with A-Mem style linking
- Automate embedding generation (remove backfill script)
- Add explicit memory compression/summarization layer
