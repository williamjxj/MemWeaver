"""Tests for wikilink parsing."""

from server.pipeline.wiki_graph import extract_wikilink_targets


def test_extract_wikilinks_basic() -> None:
    md = "See [[transformers]] and [[attention-mechanism|Attention]]."
    assert extract_wikilink_targets(md) == ["transformers", "attention-mechanism"]


def test_extract_skips_empty() -> None:
    assert extract_wikilink_targets("no links") == []
