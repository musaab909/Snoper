"""Coverage for updater install/verify flow and autostart command building."""

import snoper.updater as up


def test_verify_authenticode_false_off_windows(tmp_path):
    f = tmp_path / "Snoper-Setup.exe"
    f.write_bytes(b"x")
    # On non-Windows we never auto-run installers, so verification returns False.
    assert up.verify_authenticode(str(f)) is False


def test_install_skipped_when_not_frozen(tmp_path):
    f = tmp_path / "Snoper-Setup.exe"
    f.write_bytes(b"x")
    # Not a frozen exe -> install is a safe no-op.
    assert up.install(str(f)) is False


def test_check_and_update_full_flow(monkeypatch, tmp_path):
    from snoper.updater import UpdateInfo

    info = UpdateInfo(version="v2.0.0", download_url="https://dl/x.exe", asset_name="x.exe")
    dest = tmp_path / "x.exe"
    dest.write_bytes(b"installer")

    monkeypatch.setattr(up, "check", lambda *a, **k: info)
    monkeypatch.setattr(up, "download", lambda *a, **k: str(dest))
    monkeypatch.setattr(up, "install", lambda *a, **k: True)

    msgs = []
    assert up.check_and_update(object(), on_status=msgs.append) is True
    assert any("Downloading" in s for s in msgs)
    assert any("Installing" in s for s in msgs)


def test_check_and_update_download_fails(monkeypatch):
    from snoper.updater import UpdateInfo

    info = UpdateInfo(version="v2.0.0", download_url="https://dl/x.exe", asset_name="x.exe")
    monkeypatch.setattr(up, "check", lambda *a, **k: info)
    monkeypatch.setattr(up, "download", lambda *a, **k: None)

    msgs = []
    assert up.check_and_update(object(), on_status=msgs.append) is False
    assert any("failed" in s.lower() for s in msgs)


def test_autostart_launch_command():
    from snoper.platform import autostart_win as a

    cmd = a._launch_command()
    assert "snoper" in cmd.lower() or cmd.endswith('"')  # path or `-m snoper`


def test_autostart_apply_disable_off_windows():
    from snoper.platform import autostart_win as a

    if a._is_windows():
        import pytest

        pytest.skip("covered by Windows CI")
    # disable() is a safe no-op off Windows
    a.disable()
    a.apply(False)
