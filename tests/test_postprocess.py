"""Tests for the post-processing pipeline (no external services required)."""

from pathlib import Path

from snoper.config import Settings
from snoper.postprocess import CloudUpload, PostProcessor


def test_inactive_when_unconfigured():
    pp = PostProcessor.from_settings(Settings())
    assert pp.active is False


def test_cloud_upload_copies_to_dest(tmp_path):
    src = tmp_path / "rec.wav"
    src.write_bytes(b"audio-bytes")
    dest = tmp_path / "cloud"
    step = CloudUpload(dest_dir=str(dest))
    out = step.run(src)
    assert out == src  # cloud upload doesn't change the working path
    assert (dest / "rec.wav").read_bytes() == b"audio-bytes"


def test_from_settings_builds_steps(tmp_path):
    s = Settings()
    s.postprocess = {"cloud_dir": str(tmp_path / "out"), "encrypt_passphrase": "pw"}
    pp = PostProcessor.from_settings(s)
    assert pp.active
    names = {type(step).__name__ for step in pp.steps}
    assert "CloudUpload" in names and "Encrypt" in names


def test_chain_continues_on_step_failure(tmp_path):
    # a step that raises shouldn't abort the chain
    class Boom:
        def run(self, p):
            raise RuntimeError("boom")

    src = tmp_path / "rec.wav"
    src.write_bytes(b"x")
    dest = tmp_path / "cloud"
    pp = PostProcessor(steps=[Boom(), CloudUpload(dest_dir=str(dest))])
    pp.run(src)
    assert (dest / "rec.wav").exists()
