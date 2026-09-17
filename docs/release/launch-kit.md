# Launch kit — drafts, not sent

All copy below is staged for a future approved release. Replace future release links and
version references only after the artifacts exist. The editable canonical descriptions are
in `release/product.json`; keep listing copy consistent with actual capabilities.

## Product positioning

**Name:** CiteNexus

**Tagline:** Scholarly discovery and citations with evidence you can trace.

**Category:** Research / scholarly search / citations / MCP.

**Primary audience:** Researchers, graduate students, academic writing teams and developers
building research assistants.

**WTF-P connection:** CiteNexus supplies the sources; WTF-P manages the writing workflow.

Three concrete reasons to try it:

1. Start without an API key using Crossref, DataCite and Europe PMC.
2. Carry identifiers, source URLs, retrieval times, field attribution and provider-specific
   metrics from discovery into citation review.
3. Export observed metadata as BibTeX, RIS or CSL-JSON, then use the optional WTF-P companion
   to keep candidate references connected to research notes and manuscript work.

Optional APIs extend subject coverage and graph access: arXiv, Semantic Scholar, OpenAlex,
Google Scholar through SerpAPI, Scopus and Web of Science Starter. Unpaywall can enrich legal
OA locations. Their quotas, costs and institutional entitlements remain separate from the
software license. No LLM subscription is needed to run CiteNexus.

Do not claim exhaustive literature coverage, guaranteed citation accuracy, automatic claim
verification, full-text access, equal citation counts across indexes, native integration on
every client, a hosted service, or durable MCP background tasks.

## Listing copy

**Short (registry limit: 100 characters):**

> Search scholarly sources, verify references, and export citations with traceable evidence.

**Standard directory description:**

> CiteNexus connects research assistants to free scholarly metadata and optional academic
> APIs. Discover papers, resolve identifiers, check references, and export BibTeX, RIS or
> CSL-JSON with source provenance. No model or API key is required for default searches.

**Extended description:**

> CiteNexus is an MCP research service for source-backed discovery and citation work. It
> searches Crossref, DataCite and Europe PMC by default, with optional preprint, graph,
> commercial and institutional sources. Eleven tools cover search, identifier resolution,
> metadata verification, citation export, citation graphs, per-provider metrics and legal
> open-access locations. Structured records retain source URLs, retrieval timestamps and
> warnings about missing metadata. An optional WTF-P companion connects discovery to an
> academic writing workflow. Search matches remain candidates until reviewed; the service
> does not invent authors, infer impact factors or validate scientific claims.

**Keywords:** `mcp`, `research`, `citations`, `bibliography`, `academic`, `bibtex`,
`crossref`, `wtf-p`. Choose a channel's own categories rather than inventing category IDs.

**Assets:** `assets/cite-nexus-400.png` (400×400), `assets/social-card.png` (1200×630).
SVG sources are editable and contain no external resources. Render with ImageMagick:

```bash
convert -background none assets/cite-nexus.svg assets/cite-nexus-400.png
convert assets/social-card.svg assets/social-card.png
```

## Cline submission draft

**Repository:** https://github.com/akougkas/cite-nexus-mcp

**Logo:** attach the prepared 400×400 PNG, or use its public URL after the approved source
commit is available. Do not submit a local filesystem path as an image URL.

**Reason for addition:**

> CiteNexus helps Cline users find scholarly sources, check reference metadata and export
> citations without a mandatory API key. Its free default sources and source attribution
> make the first research workflow useful immediately. Optional academic APIs extend
> coverage without silently activating paid searches. README and llms-install.md explain
> setup, transport, provider configuration and evidence boundaries.

**Required installation attestation:** pending. Run Cline's actual README-guided installation
in a disposable profile before checking its submission form's tested-installation box.

## Curated-list contribution draft

Choose the live list's research/search category and alphabetical position. Apply only the
language/platform symbols justified by the list's current conventions and tested support.

```markdown
- [akougkas/cite-nexus-mcp](https://github.com/akougkas/cite-nexus-mcp) - Scholarly discovery, reference verification, and deterministic citation export with free default sources and traceable provider evidence.
```

**PR title:** Add CiteNexus scholarly discovery and citation server

**PR body:**

> Adds an installable MIT-licensed Python MCP server for scholarly search and citation
> workflows. Crossref, DataCite and Europe PMC work without mandatory credentials; optional
> academic APIs can be selected explicitly. The README documents stdio setup, structured
> results, provenance, deterministic export and verification limits.
>
> Validation: insert the exact released version and completed clean-install evidence here
> before submitting. No public listing or native-client certification is asserted by this draft.

## Ninety-second demo storyboard

| Time | Show | Explain |
|---|---|---|
| 0–15 s | `list-providers` | Three default sources, no key setup; optional vendors remain explicit. |
| 15–35 s | `search-papers` with `{"query":"reproducible machine learning","providers":["crossref"],"limit":3}` | Open a returned source record and show its attribution. These are candidates. |
| 35–55 s | `verify-citation` with `{"citation":"10.1038/nature14539","expected_title":"Deep learning","expected_year":2015}` | Explain metadata identity checks and show the observed result; do not script a success if the provider is unavailable. |
| 55–70 s | `get-citation` for the same DOI, `format: "bibtex"` | Show deterministic export and any warnings. |
| 70–90 s | WTF-P `citation-search --backend=cite-nexus` | Keep the source record beside candidate BibTeX, then hand off to the writing workflow. |

Record the provider and observation date in the demo. Use public queries, hide credentials
and private project paths, and retain an honest rate-limit/error take if a live service fails.
The fixture integration script is reproducible engineering evidence, not a live search video.

## Announcement drafts

**Short social post, for the future approved release:**

> CiteNexus connects your research assistant to scholarly sources through MCP. Start with
> free metadata, keep the source evidence, verify references, and export citations. The
> WTF-P companion brings those candidates into your writing workflow.
> https://github.com/akougkas/cite-nexus-mcp

**Research/developer community post:**

> I built CiteNexus around a practical problem: research assistants need source-backed
> records they can carry from discovery into a bibliography. The default search uses
> Crossref, DataCite and Europe PMC without an API key. Optional academic and institutional
> APIs extend coverage, with explicit provider selection and separate citation counts.
>
> The service resolves identifiers, checks supplied reference metadata and exports BibTeX,
> RIS or CSL-JSON without generating missing facts. Its WTF-P companion preserves candidate
> status and source records for academic writing. I'd welcome reproducible examples of
> metadata conflicts, coverage gaps and research workflows that need better support.
>
> Include the released install command, a tested client example and demo link here after launch approval.

**Show HN title draft:** Show HN: CiteNexus — source-backed scholarly search and citations over MCP

Use community rules and account context before posting. Do not cross-post identical text
indiscriminately or imply endorsements by upstream providers, client vendors or marketplaces.

## Launch measurement

Track public installation failures, source coverage gaps, provider errors, unresolved metadata
cases, listing approval outcomes and time-to-first-useful-result from consenting testers.
Use reproducible qualitative examples first. Do not add query telemetry to the local server
or invent usage metrics to support promotional copy.
