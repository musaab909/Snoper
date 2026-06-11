"""Tests for secret storage and config redaction (no real keyring needed)."""

import json

import snoper.secrets_store as ss
from snoper.config import Settings


class FakeKeyring:
    """In-memory stand-in for the keyring module."""

    def __init__(self):
        self.store = {}

    def set_password(self, service, name, value):
        self.store[(service, name)] = value

    def get_password(self, service, name):
        return self.store.get((service, name))

    def delete_password(self, service, name):
        self.store.pop((service, name), None)


def test_get_secret_prefers_env(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "from-env")
    assert ss.get_secret("update_token", env_var="MY_TOKEN") == "from-env"


def test_set_and_get_via_keyring(monkeypatch):
    fk = FakeKeyring()
    monkeypatch.setattr(ss, "keyring", fk)
    assert ss.set_secret("update_token", "abc123") is True
    assert ss.get_secret("update_token") == "abc123"


def test_no_keyring_is_graceful(monkeypatch):
    monkeypatch.setattr(ss, "keyring", None)
    assert ss.set_secret("x", "y") is False
    assert ss.get_secret("x") is None


def test_config_save_redacts_secrets_to_keyring(tmp_path, monkeypatch):
    fk = FakeKeyring()
    monkeypatch.setattr(ss, "keyring", fk)

    s = Settings(recordings_dir=str(tmp_path))
    s.update_token = "supersecret-token"
    s.postprocess = {
        "smtp": {"host": "mail", "user": "u", "password": "smtp-pass", "to": "a", "from": "b"},
        "ftp": {"host": "h", "user": "u", "password": "ftp-pass"},
        "encrypt_passphrase": "enc-pass",
    }
    cfg = tmp_path / "config.json"
    s.save(cfg)

    raw = cfg.read_text()
    # No secret value appears in the plaintext file.
    assert "supersecret-token" not in raw
    assert "smtp-pass" not in raw
    assert "ftp-pass" not in raw
    assert "enc-pass" not in raw

    # Secrets live in the keyring.
    assert fk.get_password(ss.SERVICE, "update_token") == "supersecret-token"
    assert fk.get_password(ss.SERVICE, "smtp_password") == "smtp-pass"

    # And load() restores them transparently.
    loaded = Settings.load(cfg)
    assert loaded.update_token == "supersecret-token"
    assert loaded.postprocess["smtp"]["password"] == "smtp-pass"
    assert loaded.postprocess["encrypt_passphrase"] == "enc-pass"


def test_config_save_without_secrets_is_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "keyring", FakeKeyring())
    s = Settings(recordings_dir=str(tmp_path))
    cfg = tmp_path / "config.json"
    s.save(cfg)
    data = json.loads(cfg.read_text())
    assert data["update_token"] is None
