"""Additional unit tests to cover updater network paths, config, autostart, logging."""

import json
import logging

import pytest


# --- updater: check() returns UpdateInfo on a newer release -------------------
def test_updater_check_finds_newer(monkeypatch):
    import snoper.updater as up

    payload = {
        "tag_name": "v999.0.0",
        "body": "notes",
        "assets": [
            {"name": "Snoper-Setup.exe", "url": "https://api/assets/1",
             "browser_download_url": "https://dl/Snoper-Setup.exe"},
        ],
    }

    class Resp:
        def read(self, *_):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Resp())

    class S:
        update_token = None

    info = up.check(S())
    assert info is not None
    assert info.version == "v999.0.0"
    assert info.asset_name == "Snoper-Setup.exe"


def test_updater_check_handles_network_error(monkeypatch):
    import snoper.updater as up

    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(up.urllib.request, "urlopen", boom)

    class S:
        update_token = None

    assert up.check(S()) is None


def test_updater_download_writes_file(tmp_path, monkeypatch):
    import snoper.updater as up
    from snoper.updater import UpdateInfo

    class Resp:
        def __init__(self):
            self._data = [b"chunk1", b"chunk2", b""]

        def read(self, *_):
            return self._data.pop(0)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(up.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(up.urllib.request, "urlopen", lambda *a, **k: Resp())

    class S:
        update_token = None

    info = UpdateInfo(version="v1", download_url="https://dl/x.exe", asset_name="x.exe")
    path = up.download(info, S())
    assert path is not None
    assert open(path, "rb").read() == b"chunk1chunk2"


def test_check_and_update_up_to_date(monkeypatch):
    import snoper.updater as up

    monkeypatch.setattr(up, "check", lambda *a, **k: None)
    msgs = []
    assert up.check_and_update(object(), on_status=msgs.append) is False
    assert "Up to date" in msgs


# --- config: validation + roundtrip ------------------------------------------
def test_config_invalid_mode_raises():
    from snoper.config import Settings

    s = Settings()
    s.mode = "bogus"
    with pytest.raises(ValueError):
        s.validate()


def test_config_roundtrip(tmp_path, monkeypatch):
    import snoper.secrets_store as ss
    from snoper.config import Settings

    monkeypatch.setattr(ss, "keyring", None)  # no keyring -> plain roundtrip
    s = Settings(recordings_dir=str(tmp_path), vox_threshold=0.05, silence_timeout_s=1.5)
    cfg = tmp_path / "c.json"
    s.save(cfg)
    loaded = Settings.load(cfg)
    assert loaded.vox_threshold == 0.05
    assert loaded.silence_timeout_s == 1.5


def test_config_load_missing_returns_defaults(tmp_path):
    from snoper.config import Settings

    s = Settings.load(tmp_path / "does-not-exist.json")
    assert s.mode == "vox"


# --- autostart: safe no-ops off Windows --------------------------------------
def test_autostart_noops_off_windows():
    from snoper.platform import autostart_win as a

    if a._is_windows():
        pytest.skip("covered by Windows CI")
    assert a.is_enabled() is False
    a.apply(False)  # should not raise
    with pytest.raises(RuntimeError):
        a.enable()


# --- logging: setup returns a writable path ----------------------------------
def test_logging_setup(tmp_path, monkeypatch):
    import snoper.logging_setup as ls

    monkeypatch.setattr(ls, "_CONFIGURED", False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    path = ls.setup_logging(level=logging.DEBUG)
    assert path.exists()
    logging.getLogger("snoper.test").info("hello")
    assert path.read_text()
