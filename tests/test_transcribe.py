"""Tests for the transcription engine using a fake Whisper model (no real model)."""

from dataclasses import dataclass

from snoper.config import Settings
from snoper.transcribe.engine import TranscriptionQueue


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str


class FakeInfo:
    language = "en"


class FakeModel:
    def transcribe(self, path, language=None):
        segs = [FakeSegment(0.0, 1.0, " hello "), FakeSegment(1.0, 2.0, "world")]
        return iter(segs), FakeInfo()


def _settings(tmp_path):
    return Settings(recordings_dir=str(tmp_path), transcribe=True)


def test_load_model_raises_without_whisper(tmp_path, monkeypatch):
    import snoper.transcribe.engine as eng

    monkeypatch.setattr(eng, "WhisperModel", None)
    tq = TranscriptionQueue(_settings(tmp_path))
    import pytest

    with pytest.raises(RuntimeError):
        tq._load_model()


def test_transcribe_writes_txt_json_and_indexes(tmp_path):
    tq = TranscriptionQueue(_settings(tmp_path))
    tq._model = FakeModel()  # inject fake model

    audio = tmp_path / "20260101_100000.wav"
    audio.write_bytes(b"RIFFfake")

    from datetime import datetime

    tq._transcribe(audio, datetime(2026, 1, 1, 10, 0), 2.0)

    txt = audio.with_suffix(".txt")
    js = audio.with_suffix(".transcript.json")
    assert txt.read_text(encoding="utf-8") == "hello world"
    assert "segments" in js.read_text(encoding="utf-8")

    # indexed + searchable
    results = tq._index.search("hello")
    assert len(results) == 1
    assert results[0]["transcript"] == "hello world"


def test_enqueue_and_stop(tmp_path):
    tq = TranscriptionQueue(_settings(tmp_path))
    tq.enqueue(tmp_path / "a.wav", None, 1.0)
    assert tq._q.qsize() == 1
    tq.stop()
    assert tq._stop.is_set()
