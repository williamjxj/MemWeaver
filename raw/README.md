# Raw layer (immutable sources)

Per `docs/v2/s2-claude-plan.md` §4.1, accepted Q/A pairs will eventually be written as immutable JSON under:

`raw/qa/YYYY-MM-DD/<slug>.json`

Nothing is written here by the current Milestone B API alone; the ingest pipeline will populate this tree. The **wiki** under `wiki/` documents behavior until that lands.



## qa

`raw/qa/<date>/` — immutable JSON

## failed

`raw/failed/` — dead-letter queue