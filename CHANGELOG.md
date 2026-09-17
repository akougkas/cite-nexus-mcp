# Changelog

## 0.2.1 — 2026-09-17

- Report invalid input, unknown providers and provider outcomes as readable tool errors. MCP SDK 2.2
  previously reduced them to "Error executing tool <name>".
- Name the providers that could not find an identifier and suggest search-papers for titles.
- Reject undeclared tool arguments in the input schema (`additionalProperties: false`) and on the
  server, listing the accepted names, so a misnamed `max_results` no longer returns a default page.

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
