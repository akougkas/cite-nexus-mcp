# CiteNexus 0.2.1

Release date: 2026-09-17. Source: annotated tag `v0.2.1`.

This patch fixes two tool-boundary defects found in a live MCP client session. Tool names,
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

Clients that sent extra, ignored arguments will now receive an error and must remove them.

## Install

```bash
uvx --from cite-nexus-mcp==0.2.1 cite-nexus-mcp --no-env-file
uvx --from cite-nexus-mcp==0.2.1 cite-nexus-wtfp --check
```

See the [changelog](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.1/CHANGELOG.md) and the
[0.2.0 release notes](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.1/docs/release/release-notes-0.2.0.md)
for the full feature set.
