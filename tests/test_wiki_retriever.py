from pathlib import Path
from server.config import Settings
from server.services.wiki_retriever import _load_index

settings = Settings()


def test_load_index_returns_list(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    index_file = wiki_dir / "_index.md"
    index_file.write_text(
        "| Slug | Topic | Keywords | One-line summary |\n"
        "|------|-------|----------|-----------------|\n"
        "| coding/python-patterns | coding | fastapi, async | Test article |\n"
    )
    settings.wiki_dir = wiki_dir
    rows = _load_index(settings.wiki_dir)
    assert len(rows) == 1
    assert rows[0]["slug"] == "coding/python-patterns"
    assert rows[0]["topic"] == "coding"


def test_load_index_empty(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    settings.wiki_dir = wiki_dir
    rows = _load_index(settings.wiki_dir)
    assert rows == []


def test_load_index_skips_header_and_separator(tmp_path: Path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    index_file = wiki_dir / "_index.md"
    index_file.write_text(
        "| Slug | Topic | Keywords | One-line summary |\n"
        "|------|-------|----------|-----------------|\n"
        "| coding/test | coding | test, example | A test article |\n"
    )
    settings.wiki_dir = wiki_dir
    rows = _load_index(settings.wiki_dir)
    assert len(rows) == 1
    assert rows[0]["slug"] == "coding/test"
