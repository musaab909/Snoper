# Security & Privacy

## Reporting a vulnerability

Email the maintainer (see repo owner) with details. Please do not open public
issues for security reports. We aim to acknowledge within 72 hours.

## Lawful-use notice

Snoper is an **audio recording** tool. Recording people without their knowledge
or consent is illegal in many jurisdictions (e.g. two-party-consent US states,
the EU, and the UK), regardless of who owns the device. Snoper is deliberately
**transparent**: it always shows a visible system-tray recording indicator and
ships **no hidden/stealth mode**. Only record where you have the legal right and
the consent of those being recorded.

## Update integrity

The auto-updater downloads installers from GitHub Releases over TLS and, on
Windows, **verifies the installer's Authenticode signature is `Valid` before
executing it** (`update_require_signature`, on by default). An unsigned or
tampered installer is rejected. Disable this only for local testing.

## Data handling

- Recordings and transcripts are stored locally under the configured recordings
  directory; nothing is uploaded unless you explicitly enable a post-processing
  upload step (cloud dir / FTP / email).
- Optional post-processing supports **AES encryption at rest** of recordings.
- Secrets (update token, SMTP/FTP credentials) should be provided via the OS
  keyring or environment variables rather than committed config. Avoid storing
  plaintext credentials in `config.json`.

## Build & supply chain

- Releases are built in CI on GitHub-hosted Windows runners and, when a signing
  certificate is configured, are Authenticode-signed.
- The frozen exe is smoke-tested (`--selftest`) on a real Windows runner before
  any release is published.
