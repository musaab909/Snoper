"""Background transcription worker using faster-whisper.

Finished segments are enqueued and transcribed off the audio thread. Each result
is written as a `.txt` (and `.json` with timestamps) next to the audio file and
recorded in the storage index for search.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from pathlib import Path

from ..config import Settings
from ..storage.index import RecordingIndex

log = logging.getLogger("snoper.transcribe")

try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover - optional heavy dependency
    WhisperModel = None


class TranscriptionQueue:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._q: queue.Queue[tuple] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._model = None
        self._index = RecordingIndex(settings.recordings_dir)

    def _load_model(self):
        if self._model is None:
            if WhisperModel is None:
                raise RuntimeError(
                    "faster-whisper not installed. pip install faster-whisper"
                )
            self._model = WhisperModel(self.settings.whisper_model, compute_type="int8")
        return self._model

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="snoper-transcribe", daemon=True)
        self._thread.start()

    def enqueue(self, path: Path, started_at, duration_s: float) -> None:
        self._q.put((Path(path), started_at, duration_s))

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:  # pragma: no cover - requires model + audio
        while not self._stop.is_set():
            try:
                path, started_at, duration = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._transcribe(path, started_at, duration)
            except Exception:
                log.exception("transcription failed for %s", path.name)

    def _transcribe(self, path: Path, started_at, duration: float) -> None:
        model = self._load_model()
        segments, info = model.transcribe(
            str(path), language=self.settings.whisper_language
        )
        seg_list = [
            {"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments
        ]
        text = " ".join(s["text"] for s in seg_list).strip()

        path.with_suffix(".txt").write_text(text, encoding="utf-8")
        path.with_suffix(".transcript.json").write_text(
            json.dumps({"language": info.language, "segments": seg_list}, indent=2),
            encoding="utf-8",
        )
        self._index.add(
            audio_path=path,
            started_at=started_at,
            duration_s=duration,
            transcript=text,
        )
