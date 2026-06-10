"""Single source of truth for the app version.

Bump this (or let CI set it from the git tag) for each release. The updater
compares this against the latest GitHub Release tag to decide whether to update.
"""

__version__ = "1.0.3"

# GitHub repo that publishes releases (owner/name).
GITHUB_REPO = "musaab909/Snoper"
