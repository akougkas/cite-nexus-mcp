# Changelog

## 0.2.1 — 2026-09-17

- Report invalid input, unknown providers and provider outcomes as readable tool errors. MCP SDK 2.2
  previously reduced them to "Error executing tool <name>".
- Name the providers that could not find an identifier and suggest search-papers for titles.
- Reject undeclared tool arguments in the input schema (`additionalProperties: false`) and on the
  server, listing the accepted names, so a misnamed `max_results` no longer returns a default page.
- Fix arXiv search and lookup, which failed with HTTP 406 in 0.2.0. arXiv's CDN refuses TLS
  handshakes that offer ALPN without TLS 1.3 post-handshake authentication, which is httpcore's
  default. The HTTP client now enables post-handshake authentication, as Python's `http.client` does.
- Resolve arXiv identifiers through their DataCite DOI (`10.48550/arXiv.<id>`) when arXiv does not
  answer. The record keeps both identifiers and the arXiv issue stays visible as a warning.
- **Default change:** `search-papers` accepts `detail` (`compact` or `full`, default `compact`).
  Compact records return an empty `field_sources`; `sources` still names each provider. Set
  `detail: "full"` for the 0.2.0 record. A default page for three providers drops from 45.4 KB to
  36.7 KB of structured content. The WTF-P companion requests `full`.
- Send tool results as unindented JSON text. The text block previously repeated structured content
  with two-space indentation, 75.0 KB for the same default page; it is now 36.7 KB.

## 0.2.0 — 2026-09-17

CiteNexus becomes a provider-independent scholarly metadata service with public API defaults.

- Migrate to MCP Python SDK 2.2 and protocol 2026-07-28, preserving the legacy protocol path.
- Add typed tools, output schemas, read-only annotations, resources, prompts and progress.
- Add local Streamable HTTP alongside stdio, plus configuration discovery and explicit `.env` loading.
- Add Crossref, DataCite, Europe PMC, arXiv, Semantic Scholar, OpenAlex, Scopus and Web of Science
  Starter alongside the revised SerpAPI integration; add optional Unpaywall enrichment.
- Introduce namespaced identifiers, exact lookup checks, provenance, retained source disagreements,
  version-aware deduplication, native Europe PMC cursor paging and bounded provider requests.
- Add deterministic BibTeX/RIS/CSL-JSON export, citation verification, bounded batch export,
  open-access discovery and citation/reference traversal.
- Correct the citation-count bug: provider totals replace citation-page lengths.
- Remove automatic AI formatting, inferred bibliographic facts and the paid-provider startup requirement.
- Move standalone legacy AI helpers to an optional extra; retain old MCP tool names and SerpAPI aliases.
- Add offline provider fixtures, protocol integration tests, a separate public-API smoke script,
  Python version CI, build configuration and a non-root stdio container definition.
- Rewrite product positioning, configuration, migration and source-access documentation.
- Integrate WTF-P's citation-search workflow through a bounded companion using real MCP stdio;
  preserve candidates and source records, select vendors explicitly, and test timeout cleanup.
- Add `cite-nexus-wtfp --check` and `--no-env-file` for reproducible client-managed configuration.
- Prepare versioned registry and portable/Codex/Claude plugin metadata, a 41-channel marketplace
  inventory, launch copy, icon/social assets, troubleshooting and agent installation guidance.

No release publication or registry registration is performed by this change.
