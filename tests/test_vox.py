"""Unit tests for the VOX state machine, driven by synthetic audio frames."""

import numpy as np
import pytest

from snoper.audio.vox import EventType, VoxEngine, VoxState, rms


FRAME_MS = 30
SAMPLES = 480  # 16kHz * 30ms


def loud(level=0.5):
    return np.full(SAMPLES, level, dtype=np.float32)


def quiet():
    return np.zeros(SAMPLES, dtype=np.float32)


def feed(engine, frames):
    events = []
    for f in frames:
        events.extend(engine.process(f))
    return events


def types(events):
    return [e.type for e in events]


def test_rms_basic():
    assert rms(quiet()) == 0.0
    assert rms(np.full(10, 0.5, dtype=np.float32)) == pytest.approx(0.5)
    assert rms(np.array([])) == 0.0


def test_silence_never_starts():
    eng = VoxEngine(threshold=0.02, frame_ms=FRAME_MS)
    events = feed(eng, [quiet()] * 50)
    assert events == []
    assert eng.state is VoxState.IDLE


def test_starts_after_start_frames():
    eng = VoxEngine(threshold=0.02, frame_ms=FRAME_MS, start_frames=3)
    # 2 loud frames: not enough yet
    assert feed(eng, [loud(), loud()]) == []
    # 3rd loud frame triggers START
    events = feed(eng, [loud()])
    assert types(events) == [EventType.START]
    assert eng.state is VoxState.RECORDING


def test_isolated_loud_blip_does_not_start():
    eng = VoxEngine(threshold=0.02, frame_ms=FRAME_MS, start_frames=3)
    # single loud frame interrupted by silence resets the run
    events = feed(eng, [loud(), quiet(), loud(), quiet(), loud()])
    assert events == []
    assert eng.state is VoxState.IDLE


def test_preroll_included_on_start():
    eng = VoxEngine(threshold=0.02, frame_ms=FRAME_MS, start_frames=2, preroll_ms=90)
    # 3 quiet frames buffered, then 2 loud -> start. preroll holds up to 3 frames.
    events = feed(eng, [quiet(), quiet(), quiet(), loud(), loud()])
    start = next(e for e in events if e.type is EventType.START)
    assert start.preroll is not None
    assert len(start.preroll) >= 1  # buffered lead-in retained


def test_stops_after_silence_timeout():
    eng = VoxEngine(
        threshold=0.02, frame_ms=FRAME_MS, start_frames=1, silence_timeout_s=0.06
    )
    # silence_frames = ceil(60/30) = 2; stop fires when silence_run > 2 (i.e. 3rd quiet)
    feed(eng, [loud()])
    assert eng.state is VoxState.RECORDING
    events = feed(eng, [quiet(), quiet()])
    assert EventType.STOP not in types(events)  # still within timeout
    events = feed(eng, [quiet()])
    assert EventType.STOP in types(events)
    assert eng.state is VoxState.IDLE


def test_brief_pause_does_not_split_segment():
    eng = VoxEngine(
        threshold=0.02, frame_ms=FRAME_MS, start_frames=1, silence_timeout_s=0.12
    )
    feed(eng, [loud()])
    # short pause (under timeout) then speech resumes -> stays in one segment
    events = feed(eng, [quiet(), quiet(), loud(), loud()])
    assert EventType.STOP not in types(events)
    assert eng.state is VoxState.RECORDING


def test_frames_emitted_while_recording():
    eng = VoxEngine(threshold=0.02, frame_ms=FRAME_MS, start_frames=1)
    feed(eng, [loud()])
    events = feed(eng, [loud(), loud()])
    assert types(events) == [EventType.FRAME, EventType.FRAME]


def test_flush_closes_open_segment():
    eng = VoxEngine(threshold=0.02, frame_ms=FRAME_MS, start_frames=1)
    feed(eng, [loud()])
    assert eng.state is VoxState.RECORDING
    events = eng.flush()
    assert types(events) == [EventType.STOP]
    assert eng.state is VoxState.IDLE
    assert eng.flush() == []  # idempotent when idle


def test_full_cycle_start_record_stop():
    eng = VoxEngine(
        threshold=0.02, frame_ms=FRAME_MS, start_frames=2, silence_timeout_s=0.03
    )
    events = feed(eng, [loud(), loud(), loud(), quiet(), quiet()])
    seq = types(events)
    assert seq[0] is EventType.START
    assert EventType.FRAME in seq
    assert seq[-1] is EventType.STOP
