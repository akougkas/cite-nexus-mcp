# CiteNexus 0.2.2 publication record

Published 2026-09-17 after owner authorization. Version 0.2.1 was merged to master but never
tagged or uploaded; 0.2.2 contains it.

## Public artifacts

| Surface | Verified result |
|---|---|
| [PyPI](https://pypi.org/project/cite-nexus-mcp/0.2.2/) | 0.2.2 wheel and source distribution available |
| [GitHub release](https://github.com/akougkas/cite-nexus-mcp/releases/tag/v0.2.2) | Public stable release with the wheel, sdist, SHA-256 checksums and server.json |
| [Official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.akougkas/cite-nexus-mcp) | `io.github.akougkas/cite-nexus-mcp` 0.2.2, active and latest; 0.2.0 remains active |
| [Release PR #4](https://github.com/akougkas/cite-nexus-mcp/pull/4) | Merged into master |
| [CI for the release commit](https://github.com/akougkas/cite-nexus-mcp/actions/runs/35255517177) | Passed on Python 3.13 and 3.14 |

Source commit: `be90cf832016e6e4a610198630b2ce81866bd1e9`.
Annotated tag: `v0.2.2` (tag object `e6e97475d45138b5889e781b6d96b321e3034e31`).
The release tag remains immutable; this publication record is a subsequent documentation update.

## Artifact identity

The distributions were built from the `v0.2.2` tag with `uv build`, installed and checked with
`scripts/check_distribution.py --install`, then uploaded. Their digests were checked against
PyPI metadata after publication.

```text
a9c5603ce739f8c39ca5fcb4123f0fd6afebf6d3f84d89c179bddd41c88a5391  cite_nexus_mcp-0.2.2-py3-none-any.whl
c12b362c115d9ff20ae8e7d54ef6e932b1b4f92b5d9b34c37b850e940bbb09f8  cite_nexus_mcp-0.2.2.tar.gz
```

The manual `publish.yml` workflow was dispatched first. Its build job passed and its publish
job failed with `invalid-publisher`, because PyPI has no Trusted Publisher configured for this
repository, workflow and the `pypi` environment. The owner then uploaded the locally built
distributions with an existing PyPI credential, so this release carries no Trusted Publisher
attestation. Configure the publisher before the next release to use the workflow.

The registry entry was published with the checksum-verified publisher CLI 1.8.1 after GitHub
namespace authentication, then read back through the public registry API. That CLI treats
GitHub's device-flow `slow_down` response as fatal; the login was completed with a device
token obtained separately for the same client and scopes.

## Verification

- 141 tests, ruff, mypy, the metadata and marketplace checks, the build and the distribution
  install check passed on the release commit.
- `uvx --refresh --from cite-nexus-mcp==0.2.2 cite-nexus-mcp --version` printed 0.2.2 from a
  directory outside any checkout, and `--list-providers` listed the providers.
- Live over MCP stdio before release: `search-papers` with `providers: ["arxiv"]` returned
  results, `get-citation arXiv:1712.05889` resolved, an unknown DOI returned a not-found error
  naming the providers tried, and an undeclared `max_results` argument was rejected with the
  accepted names.
- A recorded Clio Coder session used this build through MCP with WTF-P 0.7.3. Two calls with
  an undeclared argument were rejected by schema, the model recovered, and results entered
  model context at 2.2 to 2.9 KB.

## Known limits

- The arXiv fix depends on a measured CDN rule: HTTP 406 for a TLS ClientHello that offers ALPN
  without post-handshake auth. If the rule changes, arXiv identifiers still resolve through
  their DataCite DOI. `scripts/smoke_public.py` is the live check.
- `search-papers` now defaults to `detail: "compact"`. Callers that need `field_sources` pass
  `detail: "full"`, as the WTF-P companion does.
