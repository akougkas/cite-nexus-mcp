# CiteNexus 0.2.0 publication record

Published 2026-09-17 after owner authorization. The WTF-P team is independently qualifying
its 0.7.0 release; its publication is not a prerequisite for this package.

## Public artifacts

| Surface | Verified result |
|---|---|
| [PyPI](https://pypi.org/project/cite-nexus-mcp/0.2.0/) | 0.2.0 wheel and source distribution available |
| [GitHub release](https://github.com/akougkas/cite-nexus-mcp/releases/tag/v0.2.0) | Public stable release, wheel, sdist, SHA-256 checksums and server.json |
| [Official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.akougkas/cite-nexus-mcp) | `io.github.akougkas/cite-nexus-mcp` 0.2.0, active and latest |
| [Release PR #1](https://github.com/akougkas/cite-nexus-mcp/pull/1) | Merged into master |
| [CI for the release commit](https://github.com/akougkas/cite-nexus-mcp/actions/runs/35218991400) | All seven jobs passed |

Source commit: `234b2f870aa3bb1c40a221012899d20fda574d7e`.
Annotated tag: `v0.2.0` (tag object `7521a6b2b572a7c1fbdc740ea00ebc98afde7b91`).
The release tag remains immutable; this publication record is a subsequent documentation update.

## Artifact identity

These are the exact Linux CI artifacts, inspected and installed again before upload. Their
digests were checked against PyPI metadata after publication.

```text
3615a9e5e41d8e3cfa0fab169390499e89ce9242736a2436319ff8f02adf9676  cite_nexus_mcp-0.2.0-py3-none-any.whl
d80130dbd13159953ae1f798307cbb8ec475192f6a88d807b23eb74ca208e3e2  cite_nexus_mcp-0.2.0.tar.gz
```

The first upload used the authorized operator's existing PyPI credential. It did not use
OIDC and carries no PyPI Trusted Publisher attestation. The manual publishing workflow is
available for future releases after the account owner configures the matching publisher.
The official registry entry was published with verified publisher CLI 1.8.1 after namespace
authentication, then read back through the public registry API.

## Verification

- 130 tests passed on each Python version 3.11, 3.12, 3.13 and 3.14 in hosted CI.
- Clean installed-wheel MCP startup and companion diagnostics passed on Linux, macOS and
  Windows. These checks do not certify native client lifecycle or the full WTF-P workflow
  on every operating system.
- A fresh environment installed `cite-nexus-mcp==0.2.0` from `https://pypi.org/simple/`, without
  a checkout or local wheel. The actual installed server exposed all 11 tools, the companion
  returned schema `cite-nexus.wtfp/v1` with nine providers, and a live Crossref search returned
  a paper with no provider issues.
- The release smoke check also returned DataCite and arXiv records. Europe PMC timed out;
  anonymous Semantic Scholar returned HTTP 429. Those outcomes remain visible to callers.
- The pinned core dependency audit reported no known vulnerabilities on the release date.

## WTF-P handoff

The CiteNexus publication dependency is cleared. Qualify WTF-P's packed 0.7.0 artifact against
the publicly installed package, using its installed `cite-nexus-wtfp` executable. Complete the
WTF-P team's own native-client, evaluation, preflight and npm authentication requirements.
No WTF-P checkout, npm login or package publication was changed by this release operation.

```bash
uvx --refresh --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --version
uvx --refresh --from cite-nexus-mcp==0.2.0 cite-nexus-wtfp --check
```

Other marketplace submissions and promotional posts remain deferred. The inventory records
one active official-registry listing and forty other channels/leads to evaluate separately.
