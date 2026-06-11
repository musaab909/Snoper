# Contributing to Snoper

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Before you push

```bash
ruff check .          # lint
ruff format --check . # formatting
mypy snoper           # type check
pytest --cov=snoper   # tests + coverage
```

All four run in CI and gate merges. Keep functions focused (<50 lines), files
cohesive (<800 lines), and handle errors explicitly (log via `logging`, never
`print`).

## Tests

- Pure logic (VOX, DSP, scheduler, updater, single-instance) must have unit tests.
- Audio/hardware paths use synthetic input — no real microphone in CI.
- The frozen exe is smoke-tested on a real Windows runner (`Snoper.exe --selftest`).

## Releasing

Maintainers cut a release by pushing a tag:

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

CI builds, smoke-tests on Windows, signs (if a cert secret is configured), and
publishes a GitHub Release. Installed copies silently auto-update.

## Scope rule

Snoper is a **transparent** recorder. Pull requests that add a hidden/stealth
mode, remove the recording indicator, or otherwise enable covert recording will
not be accepted.
