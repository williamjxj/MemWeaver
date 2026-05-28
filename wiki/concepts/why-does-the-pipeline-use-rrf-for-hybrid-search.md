---
id: why-does-the-pipeline-use-rrf-for-hybrid-search
title: "Why does the pipeline use RRF for hybrid search?"
type: concept
tags: ["general"]
confidence: medium
created: 2026-05-28
updated: 2026-05-28
sources: ["ing_20260528_18ec0ff5"]
---

## Summary

RRF (Reciprocal Rank Fusion) is a popular choice for hybrid search because it effectively combines ranked results from multiple retrieval sources, such as BM25 (keyword-based) and dense vector embeddings (semantic-based). Here's why pipelines commonly use RRF: ### 1. Merges Multiple Ranking Signals Hybrid search typically retrieves results from different indexes. RRF unifies these into a single ra…

## Key claims

- (none)
