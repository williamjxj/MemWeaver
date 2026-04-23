"""Unit tests for `server.pipeline.textutil`."""

from server.pipeline.textutil import one_line, slugify


def test_slugify_ascii() -> None:
    assert slugify("Hello World!") == "hello-world"


def test_one_line_truncates() -> None:
    long = "word " * 50
    out = one_line(long, max_len=20)
    assert len(out) <= 21
    assert "…" in out or len(out) <= 20
