"""Tests for the SQLite recording index + search."""

from datetime import datetime

from snoper.storage.index import RecordingIndex


def test_add_and_search(tmp_path):
    idx = RecordingIndex(str(tmp_path))
    idx.add(tmp_path / "a.wav", datetime(2026, 1, 1, 10, 0), 12.0, "hello world meeting notes")
    idx.add(tmp_path / "b.wav", datetime(2026, 1, 1, 11, 0), 5.0, "completely different topic")

    results = idx.search("meeting")
    assert len(results) == 1
    assert results[0]["path"].endswith("a.wav")

    assert len(idx.all()) == 2


def test_search_no_match(tmp_path):
    idx = RecordingIndex(str(tmp_path))
    idx.add(tmp_path / "a.wav", datetime(2026, 1, 1), 1.0, "alpha")
    assert idx.search("zzzznomatch") == []
