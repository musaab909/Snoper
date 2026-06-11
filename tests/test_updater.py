"""Tests for the updater version logic (no network)."""

from snoper.updater import install, is_newer, parse_version, sha256


def test_parse_version():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("v2.0") == (2, 0)
    assert parse_version("") == (0,)


def test_is_newer():
    assert is_newer("v1.0.1", "1.0.0") is True
    assert is_newer("v1.1.0", "1.0.9") is True
    assert is_newer("v2.0.0", "1.9.9") is True
    assert is_newer("v1.0.0", "1.0.0") is False
    assert is_newer("v0.9.0", "1.0.0") is False


def test_check_returns_none_on_same_version(monkeypatch):
    import snoper.updater as up

    class FakeResp:
        def __init__(self, payload):
            import json
            self._b = json.dumps(payload).encode()

        def read(self, *_):
            return self._b

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    # latest tag equals current version -> no update
    monkeypatch.setattr(
        up.urllib.request, "urlopen",
        lambda *a, **k: FakeResp({"tag_name": f"v{up.__version__}", "assets": []}),
    )

    class S:
        update_token = None

    assert up.check(S()) is None


def test_sha256_matches_hashlib(tmp_path):
    import hashlib

    f = tmp_path / "x.bin"
    f.write_bytes(b"snoper-bytes")
    assert sha256(str(f)) == hashlib.sha256(b"snoper-bytes").hexdigest()


def test_install_noop_off_windows(tmp_path):
    # On non-Windows (CI dev/macOS) install must be a safe no-op, never executing.
    f = tmp_path / "Snoper-Setup.exe"
    f.write_bytes(b"not really an installer")
    assert install(str(f)) is False
