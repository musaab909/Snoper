"""Secret storage backed by the OS keyring.

Keeps credentials (update token, SMTP/FTP passwords, encryption passphrase) out
of the plaintext ``config.json``. Values are stored in the OS keyring (Windows
Credential Manager, macOS Keychain, Secret Service on Linux). Resolution order
for reads is: explicit value -> environment variable -> keyring.

If ``keyring`` isn't installed, this degrades gracefully: stores become no-ops
and reads fall back to environment variables. Nothing is ever written to disk in
plaintext by this module.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("snoper.secrets")

SERVICE = "Snoper"

keyring: Any
try:
    import keyring
except Exception:  # pragma: no cover - optional dependency
    keyring = None


def available() -> bool:
    return keyring is not None


def set_secret(name: str, value: str | None) -> bool:
    """Store (or delete, if value is falsy) a secret by name. Returns success."""
    if keyring is None:
        return False
    try:
        if value:
            keyring.set_password(SERVICE, name, value)
        else:
            try:
                keyring.delete_password(SERVICE, name)
            except Exception:
                pass
        return True
    except Exception:
        log.warning("could not write secret %r to keyring", name)
        return False


def get_secret(name: str, env_var: str | None = None, default: str | None = None) -> str | None:
    """Resolve a secret: explicit env var first, then keyring, then default."""
    if env_var:
        val = os.environ.get(env_var)
        if val:
            return val
    if keyring is not None:
        try:
            val = keyring.get_password(SERVICE, name)
            if val:
                return val
        except Exception:
            log.warning("could not read secret %r from keyring", name)
    return default
