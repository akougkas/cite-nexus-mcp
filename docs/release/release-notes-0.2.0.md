# CiteNexus 0.2.0

**Release notes draft. Remove this banner only for the approved publication.**

CiteNexus provides scholarly discovery and citations with evidence you can trace. Search
free metadata sources, resolve identifiers, check references and export citations through MCP.

## Research capabilities

- Crossref, DataCite and Europe PMC work as default sources without mandatory API keys.
- Optional arXiv, Semantic Scholar, OpenAlex, SerpAPI, Scopus and Web of Science Starter
  adapters extend discovery. Account quotas, costs and institutional entitlements vary.
- Eleven tools cover discovery, identifier resolution, reference checks, deterministic
  BibTeX/RIS/CSL-JSON exports, citation graphs, provider-specific metrics and OA locations.
- Structured records retain source URLs, retrieval times, field attribution, incomplete-author
  warnings and provider failures. Search matches remain candidates until reviewed.
- MCP 2026-07-28 support includes stdio, local Streamable HTTP, resources, prompts and bounded
  batch progress. Durable background tasks are not advertised.

## WTF-P companion

The `cite-nexus-wtfp` companion supplies a bounded MCP boundary for WTF-P's optional CiteNexus
search backend. The WTF-P-side integration targets **WTF-P 0.7.0**; published WTF-P 0.6.0 does
not contain it. Use the integration branch until the team publishes that release.

The companion preserves candidate status and provider evidence, forwards only intended
credentials through the WTF-P boundary, rejects offline network calls, and closes the server
on deadlines or cancellation. It does not write bibliography files or silently switch vendors.

## Install after publication

Python 3.11+ and uv:

```bash
uvx --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --no-env-file
uvx --from cite-nexus-mcp==0.2.0 cite-nexus-wtfp --check
```

The first command starts an MCP server and waits for a client. The second checks local MCP
startup and provider configuration without API calls. For a persistent companion executable,
install the pinned package into the Python environment used by your writing workflow.

## Migration and limits

AI formatting is no longer part of citation export. Legacy direct-AI helpers remain optional;
core operation needs no model subscription. Existing tool names retain documented compatibility
paths, but source semantics and structured results are clarified in the migration guide.

Verification checks metadata identity and supplied title/year; it does not establish scientific
truth or claim support. Citation counts are provider-specific observations. The HTTP CLI serves
a local trust boundary and is not a public hosted service with multi-user authentication.

See the [README](https://github.com/akougkas/cite-nexus-mcp/tree/v0.2.0),
[migration guide](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/migration.md),
and [WTF-P setup](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/wtf-p.md).
