# Raw 层（不可变来源）

根据 `docs/research/v2/s2-claude-plan.md` §4.1，已接受的 QA 对最终将以不可变 JSON 形式写入：

`raw/qa/YYYY-MM-DD/<slug>.json`

当前 Milestone B API 本身不会在此写入内容；摄入管线将填充此目录树。在管线完成之前，**wiki** 下的 `wiki/` 目录记录了行为说明。

---

## qa

`raw/qa/<date>/` — 不可变 JSON

## failed

`raw/failed/` — 死信队列
