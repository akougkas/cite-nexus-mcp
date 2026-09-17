# CiteNexus 0.2.1

Release date: 2026-09-17. Source: annotated tag `v0.2.1`.

This patch fixes three defects found in a live MCP client session. Tool names,
search defaults and record shapes are unchanged from 0.2.0.

## Fixes

- **Readable tool errors.** MCP SDK 2.2 reduced every service failure to
  `Error executing tool <name>`, so a client could not tell a missing record from invalid input
  or a provider outage. Tool errors now carry the reason, for example
  `not_found: doi:10.1109/hpdc.2019.00023 was not found by providers: crossref, datacite, europe_pmc.`
  Not-found identifiers suggest search-papers for title lookup. Unknown providers, malformed
  identifiers and invalid BibTeX are reported the same way. Outages keep per-provider detail.
- **Undeclared arguments are rejected.** Every tool's input schema now sets
  `additionalProperties: false`, and the server refuses unknown keys before any provider request.
  The error lists the accepted names. Previously `search-papers` with `max_results` silently
  returned a default-sized page.
- **arXiv works again.** arXiv's CDN answered every uncached request from 0.2.0 with HTTP 406,
  so arXiv searches and lookups raised unexpected exceptions. The CDN refuses TLS handshakes that
  offer ALPN without TLS 1.3 post-handshake authentication, which is httpcore's default. CiteNexus
  now enables post-handshake authentication, as Python's `http.client` does. As a safety net,
  arXiv identifier lookups fall back to the paper's DataCite DOI `10.48550/arXiv.<id>` when arXiv
  does not answer.

Clients that sent extra, ignored arguments will now receive an error and must remove them.

## Install

```bash
uvx --from cite-nexus-mcp==0.2.1 cite-nexus-mcp --no-env-file
uvx --from cite-nexus-mcp==0.2.1 cite-nexus-wtfp --check
```

See the [changelog](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.1/CHANGELOG.md) and the
[0.2.0 release notes](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.1/docs/release/release-notes-0.2.0.md)
for the full feature set.
