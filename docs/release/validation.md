# Local preparation validation — 2026-09-16

This records the preparation run, not a published release or a native client certification.
CiteNexus changes remain in its working tree. WTF-P changes are on local branch
`prep/cite-nexus-integration`: implementation commit `0b13a7483bf7c51daa87e665a7cdcb6eb253bd2c`,
followed by evaluation reseal commit `2d26713`. Neither commit was pushed or tagged.

## Completed checks

| Area | Observed result |
|---|---|
| CiteNexus full suite, Python 3.13 | 114 tests passed |
| Python 3.11 and 3.14 | 112-test full suite passed on each; the two subsequently added hung-server deadline/SIGTERM regressions also passed on each |
| Static checks | Ruff lint, format check and mypy passed |
| Registry metadata | Validated against the pinned official schema; version and PyPI ownership marker checked |
| Portable plugin | Agent Plugins manifest/MCP schemas passed; Codex plugin-creator validator passed; direct configured MCP connection exposed 11 tools |
| WTF-P full suite | `npm run test:all` passed, including protocol/evaluation, generated adapters, installer, compatibility and integration tests |
| WTF-P packaging | npm dry-run included the canonical helper and all seven generated companion modules; nine generated inventories remained current |
| Cross-project fixture | Generated Clio and Claude dispatchers called the companion, real MCP stdio and a fixture-backed provider successfully |
| Offline behavior | Network command refused before companion execution |
| Deadline / cancellation | Hung provider returned timeout status 124; companion and SDK-owned server exited without an orphan process |
| Live companion search | One public Crossref query returned a candidate with source evidence and no provider issue; observed bridge elapsed time 2,378 ms, a single observation rather than a benchmark |
| Clean installed wheel | Version 0.2.0, 11 MCP tools, local citation normalization and companion diagnostic passed; LiteLLM absent |
| Artifacts | Wheel entry points and ownership marker present; sdist contains release materials and excludes private environment/client files; local plugin review ZIP built |
| Core dependency audit | No known vulnerabilities reported for the 32 resolved third-party core packages at the time of the check |
| Distribution research | 41 channels/leads recorded; GET outcomes and redirects saved; no logins, claims, submissions or promotions performed |

The timeout regression initially found that native asyncio cancellation could interrupt
the SDK's shielded shutdown. The bridge now uses AnyIO cancellation scopes, and the
regression checks the actual server PID after both deadlines and SIGTERM.

Tests use synthetic metadata and bounded local processes. A fixture pass does not establish
live account entitlement, source completeness, or native client approval/lifecycle behavior.
The live Crossref observation does not imply a latency guarantee or availability for other APIs.

## Qualification still pending

- Actual disposable native client installs for every advertised host, including Cline's
  README-guided setup requirement and the new companion on Windows/macOS.
- Docker image and Toolkit validation; a local Docker daemon was not available in this session.
- MCPB authoring/install tests for channels that require it.
- Live paid and institutional provider tests with appropriate accounts and entitlements.
- Hosted authentication, per-user credentials and remote service operations for public
  hosted connector/plugin directories.
- Final release versions/commits, public artifact ownership verification and an explicit
  later release instruction. Offline schema validation cannot check unpublished PyPI metadata
  against a live registry.

Use the [release checklist](README.md) and [marketplace inventory](marketplaces.md) to turn
these remaining qualifications into the launch sequence. Re-run time-sensitive checks at
the final release commit.
