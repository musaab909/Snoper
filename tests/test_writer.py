"""Tests for SegmentWriter: real WAV files from synthetic VOX events."""

import wave

import numpy as np

from snoper.config import MODE_DICTATION, MODE_VOX, Settings
from snoper.audio.vox import EventType, VoxEvent


SAMPLES = 480


def loud():
    return np.full(SAMPLES, 0.5, dtype=np.float32)


def make_settings(tmp_path, mode=MODE_VOX, **kw):
    return Settings(
        recordings_dir=str(tmp_path),
        samplerate=16000,
        channels=1,
        frame_ms=30,
        mode=mode,
        min_segment_s=0.0,
        **kw,
    )


def _read_wav_frames(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes()


def test_vox_segment_creates_file(tmp_path):
    from snoper.audio.writer import SegmentWriter

    done = []
    w = SegmentWriter(make_settings(tmp_path), on_segment_complete=lambda *a: done.append(a))
    w.handle([VoxEvent(EventType.START, preroll=[loud()])])
    w.handle([VoxEvent(EventType.FRAME, frame=loud()) for _ in range(3)])
    w.handle([VoxEvent(EventType.STOP)])
    w.close()

    files = list(tmp_path.glob("*.wav"))
    assert len(files) == 1
    # 1 preroll + 3 frames = 4 frames * 480 samples
    assert _read_wav_frames(files[0]) == 4 * SAMPLES
    assert len(done) == 1


def test_short_segment_discarded(tmp_path):
    from snoper.audio.writer import SegmentWriter

    s = make_settings(tmp_path)
    s.min_segment_s = 10.0  # force discard
    w = SegmentWriter(s)
    w.handle([VoxEvent(EventType.START, preroll=[loud()])])
    w.handle([VoxEvent(EventType.STOP)])
    w.close()
    assert list(tmp_path.glob("*.wav")) == []


def test_dictation_mode_single_file_with_index(tmp_path):
    from snoper.audio.writer import SegmentWriter

    w = SegmentWriter(make_settings(tmp_path, mode=MODE_DICTATION))
    # two separate utterances
    for _ in range(2):
        w.handle([VoxEvent(EventType.START, preroll=[])])
        w.handle([VoxEvent(EventType.FRAME, frame=loud()) for _ in range(2)])
        w.handle([VoxEvent(EventType.STOP)])
    w.close()

    wavs = list(tmp_path.glob("*.wav"))
    idx = list(tmp_path.glob("*.segments.json"))
    assert len(wavs) == 1   # single continuous file
    assert len(idx) == 1    # timestamp index sidecar
