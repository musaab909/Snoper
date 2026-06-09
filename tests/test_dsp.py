"""Tests for DSP: noise suppression + AGC."""

import numpy as np

from snoper.audio.dsp import AutomaticGainControl, DspChain, NoiseSuppressor


def test_agc_boosts_quiet_signal():
    agc = AutomaticGainControl(target_rms=0.1, max_gain=8.0, smoothing=0.0)
    quiet = np.full(480, 0.01, dtype=np.float32)
    out = agc.process(quiet)
    assert np.sqrt(np.mean(out**2)) > np.sqrt(np.mean(quiet**2))


def test_agc_never_clips():
    agc = AutomaticGainControl(target_rms=0.5, max_gain=100.0, smoothing=0.0)
    loud = np.full(480, 0.9, dtype=np.float32)
    out = agc.process(loud)
    assert out.max() <= 1.0 and out.min() >= -1.0


def test_noise_suppressor_learns_then_reduces_noise():
    rng = np.random.default_rng(0)
    ns = NoiseSuppressor(learn_frames=10, over_subtraction=1.5)
    noise = lambda: (rng.normal(0, 0.05, 480)).astype(np.float32)
    # learning phase: passes through
    for _ in range(10):
        ns.process(noise())
    assert ns.ready
    # a noise-only frame after learning should have reduced energy
    n = noise()
    out = ns.process(n)
    assert np.sqrt(np.mean(out**2)) <= np.sqrt(np.mean(n**2)) + 1e-6


def test_dsp_chain_inactive_is_identity_passthrough():
    chain = DspChain(noise=False, agc=False)
    assert not chain.active
    f = np.full(480, 0.2, dtype=np.float32)
    assert np.array_equal(chain.process(f), f)


def test_dsp_chain_active_flag():
    assert DspChain(noise=True, agc=False).active
    assert DspChain(noise=False, agc=True).active
