"""Coverage for individual post-processing steps (no external services)."""


from snoper.postprocess import CompressMp3, EmailDelivery, Encrypt, PostProcessor


def test_compress_mp3_skips_without_ffmpeg(tmp_path, monkeypatch):
    import snoper.postprocess as pp

    monkeypatch.setattr(pp, "_have_ffmpeg", lambda: False)
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    assert CompressMp3().run(src) == src  # unchanged when ffmpeg absent


def test_compress_mp3_noop_on_mp3_input(tmp_path):
    src = tmp_path / "a.mp3"
    src.write_bytes(b"x")
    assert CompressMp3().run(src) == src


def test_encrypt_skips_without_cryptography(tmp_path, monkeypatch):
    # Simulate cryptography not installed by breaking the import.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("cryptography"):
            raise ImportError("no cryptography")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    src = tmp_path / "a.wav"
    src.write_bytes(b"data")
    out = Encrypt("pw").run(src)
    assert out == src  # graceful skip, original returned
    assert src.exists()


def test_encrypt_roundtrip_if_available(tmp_path):
    crypto = __import__("importlib").util.find_spec("cryptography")
    if crypto is None:
        import pytest

        pytest.skip("cryptography not installed")
    from cryptography.fernet import Fernet

    src = tmp_path / "a.wav"
    src.write_bytes(b"secret-audio")
    step = Encrypt("passphrase", delete_source=True)
    out = step.run(src)
    assert out.suffix == ".enc"
    assert not src.exists()
    # decrypt back
    key = step._key()
    assert Fernet(key).decrypt(out.read_bytes()) == b"secret-audio"


def test_email_delivery_failure_is_caught(tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    # invalid SMTP config -> step logs and returns path without raising
    step = EmailDelivery({"host": "127.0.0.1", "port": 1, "user": "u", "password": "p",
                          "to": "a@b", "from": "c@d"})
    assert step.run(src) == src


def test_postprocessor_runs_steps_in_order(tmp_path):
    calls = []

    class Step:
        def __init__(self, tag):
            self.tag = tag

        def run(self, p):
            calls.append(self.tag)
            return p

    src = tmp_path / "a.wav"
    src.write_bytes(b"x")
    PostProcessor([Step("one"), Step("two")]).run(src)
    assert calls == ["one", "two"]
