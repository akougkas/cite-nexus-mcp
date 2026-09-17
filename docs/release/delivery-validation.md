# Release delivery preparation — 2026-09-17

This supplements the [2026-09-16 implementation validation](validation.md). No public release
or account configuration was changed. Preparation is on local branch `prep/citenexus-0.2.0`;
the WTF-P integration remains on its separate local branch and was not modified in this pass.

## Checks completed

- GitHub API confirmed CiteNexus's public repository and **master** default branch. PyPI's
  public project endpoint returned 404. npm confirmed WTF-P `latest` is **0.6.0**.
- The full CiteNexus suite passed **130 tests** on Python 3.13. Ruff lint/format and mypy passed.
- Actionlint **1.7.12** accepted both CI and the new manual publishing workflow. Its official
  release download was checked against the upstream checksum before execution.
- `release_gate.py --tag v0.2.0` refused the current preparation-only release state as intended.
- Disposable Git repository tests exercised a valid annotated tag and rejected lightweight
  tags and a tag pointing at a different HEAD. No release tag was created in this repository.
- Artifact inspection passed for the wheel/source pair. An isolated wheel install exposed
  **11 MCP tools**, normalized a local citation, and passed the **nine-provider** companion
  diagnostic without provider API calls or a LiteLLM dependency.
- `twine check` accepted both distribution files and their package descriptions.
- The WTF-P handoff bundle passed `git bundle verify`. Its tip is
  `2d2671312b37001df15a712e8628b9d72b74e736`, with prerequisite base
  `3eac8b83df1c39a8e5c0444f2877536cd3b65630`. It includes the implementation and reseal commits.

The new Linux/macOS/Windows installed-package CI matrix is configured but has not run on
GitHub: no workflow changes were pushed. Local Linux checks are not evidence of native macOS
or Windows client installation. PyPI publisher ownership and environment protection require
account-owner configuration. The publication workflow's OIDC exchange and upload cannot be
proved by static validation or a local installation; those happen during the approved run.

The [runbook](release-0.2.0.md) separates these remaining account and public-release actions
from completed local preparation, and separates optional distribution channels from the core
Python package release.
