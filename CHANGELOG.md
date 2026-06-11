# Changelog

All notable changes are documented here. This project uses semantic versioning
via git tags (`vMAJOR.MINOR.PATCH`); pushing a tag publishes a signed release.

## [Unreleased]
### Added
- Centralized rotating-file logging with a global crash handler (uncaught
  exceptions on main and worker threads are recorded).
- Single-instance guard to prevent two recorders running at once.
- Update integrity: the auto-updater verifies the installer's Authenticode
  signature is `Valid` before executing it (`update_require_signature`).
- `pyproject.toml` with ruff + mypy + pytest/coverage config.
- `LICENSE` (MIT), `SECURITY.md`, `CONTRIBUTING.md`, this changelog.
- CI gates: lint (ruff), type-check (mypy), coverage, run concurrency, pip cache.

### Changed
- Replaced ad-hoc `print()` diagnostics with structured logging.

## [1.0.8] - 2026-06-11
### Added
- Optional Authenticode signing of the exe and installer in CI (cert via secrets).

## [1.0.7] - 2026-06-11
### Fixed
- Installer force-closes a running Snoper so upgrades/silent updates can replace
  the exe ("unable to close applications" error).

## [1.0.6] - 2026-06-10
### Added
- Synthetic-audio capture tests (stereo→mono mix + frame re-chunking).

## [1.0.5] - 2026-06-10
### Fixed
- Bundle all `snoper` submodules in the frozen exe (analyzer was missing).
### Added
- Real-Windows exe smoke test (`--selftest`) gating every release.

## [1.0.2] - 2026-06-09
### Added
- Periodic silent update re-check while running.

## [1.0.1] - 2026-06-09
### Added
- Silent auto-update via GitHub Releases.

## [1.0.0] - 2026-06-09
### Added
- Initial release: VOX recorder, modes, DSP, spectrum analyzer, scheduling,
  post-processing, transcription, searchable archive, tray UI, Windows installer.
