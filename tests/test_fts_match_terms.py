"""Unit tests for FTS5 MATCH string builder."""

from server.db.database import fts_match_terms


def test_fts_match_terms_empty() -> None:
    assert fts_match_terms("") == '""'


def test_fts_match_terms_two_words() -> None:
    m = fts_match_terms("foo bar")
    assert "OR" in m
    assert '"foo"' in m
    assert '"bar"' in m


def test_fts_match_terms_escapes_quote() -> None:
    m = fts_match_terms('say "hi"')
    assert '""' in m
