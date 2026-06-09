"""Tests for the updater version logic (no network)."""

from snoper.updater import is_newer, parse_version


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
