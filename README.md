# CiteNexus MCP

<img src="https://raw.githubusercontent.com/akougkas/cite-nexus-mcp/v0.2.0/assets/cite-nexus.svg" alt="CiteNexus" width="88" height="88" align="right">

**Scholarly discovery and citations with evidence you can trace.**

CiteNexus connects research assistants to open scholarly metadata, specialist academic indexes,
and optional commercial databases through the Model Context Protocol. Search without an API key,
resolve stable identifiers, check references against their sources, and export citations without
asking a language model to invent the missing fields.

This is a citation and metadata service for the assistant you already use. It works alongside
reference managers such as Zotero and writing environments that support MCP.

**CiteNexus 0.2.0** includes the MCP service and the `cite-nexus-wtfp` companion.
The WTF-P integration targets its separate 0.7.0 release. Marketplace listings and native
client plugin qualification are tracked independently.

[Quick start](#quick-start) · [WTF-P integration](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/wtf-p.md) ·
[Provider guide](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/providers.md) · [Troubleshooting](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/troubleshooting.md) ·
[Release information](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/release/README.md)

- **Useful without credentials:** Crossref, DataCite and Europe PMC are the default search sources.
  arXiv and Semantic Scholar are also available without mandatory keys.
- **Optional specialist and commercial access:** OpenAlex, Google Scholar through SerpAPI,
  Scopus and Web of Science Starter have explicit configuration and provider selection.
- **Source-backed records:** namespaced identifiers, retrieval timestamps, field attribution,
  incomplete-author warnings and provider-specific citation counts.
- **Deterministic export:** BibTeX, RIS and CSL-JSON from retrieved metadata. No model is required.
- **Current MCP:** Python SDK 2.2, the **2026-07-28** specification, structured tool results,
  resources, prompts, progress, stdio and Streamable HTTP. Earlier clients remain supported by
  the SDK's legacy protocol path.

## Quick start

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required.

```bash
uvx --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --version
uvx --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --no-env-file --list-providers
```

For an MCP client with a `mcpServers` configuration:

```json
{
  "mcpServers": {
    "cite-nexus": {
      "command": "uvx",
      "args": ["--from", "cite-nexus-mcp==0.2.0", "cite-nexus-mcp", "--no-env-file"]
    }
  }
}
```

The client starts MCP over stdio. No API key or `.env` file is required. Running the server
command directly waits for a client; it is not an interactive search shell. If your client
cannot find `uvx`, use its absolute executable path. The first run downloads the package and
its dependencies.

For a persistent installation, including the WTF-P companion:

```bash
uv tool install cite-nexus-mcp==0.2.0
cite-nexus-wtfp --check
```

The diagnostic starts the actual MCP service and lists providers without querying vendor APIs.
See the [WTF-P setup](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/wtf-p.md) for the separate integration and executable-path setting.

For local HTTP clients:

```bash
uvx --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --no-env-file --transport streamable-http --port 8000
```

Connect to `http://127.0.0.1:8000/mcp`. The CLI binds only to loopback and serves a single trust
boundary. A public, multi-user deployment needs authentication, credential isolation and its
own deployment integration; the CLI does not supply those features.

## Sources and access

| Provider ID | Coverage | Access | Setup |
|---|---|---|---|
| `crossref` | Publisher-deposited DOI metadata and citation counts | Free; default | Optional `CITE_NEXUS_CONTACT_EMAIL` for the polite pool |
| `datacite` | Datasets, software and other DOI-registered research outputs | Free; default | None |
| `europe_pmc` | Biomedical literature, PubMed/PMC records, references and citations | Free; default | None |
| `arxiv` | Preprints in physics, mathematics, computing and related fields | Free | Select explicitly; paced to one request per three seconds |
| `semantic_scholar` | Academic Graph discovery and citation traversal | Free/shared anonymous limits; optional key | Optional `SEMANTIC_SCHOLAR_API_KEY` |
| `openalex` | Multidisciplinary research graph | Free credits / metered account access | `OPENALEX_API_KEY` |
| `serpapi` | Google Scholar through a vendor API | Commercial; account allowances vary | `SERPAPI_API_KEY` |
| `scopus` | Elsevier's curated literature index | Institutional/commercial entitlement | `SCOPUS_API_KEY`; optional `SCOPUS_INSTTOKEN` |
| `wos` | Clarivate Web of Science Starter | Institutional/commercial entitlement | `WOS_API_KEY` |

`find-open-access` can additionally enrich DOI records with **Unpaywall** when
`UNPAYWALL_EMAIL` is configured. It returns reported legal OA locations and licensing information;
it does not download PDFs or bypass access restrictions.

Free access is subject to provider rate limits and terms. Anonymous Semantic Scholar can be
heavily throttled. OpenAlex access policies have changed over time; CiteNexus requires a key for
that adapter even when an anonymous request happens to succeed. Institution keys do not by
themselves guarantee subscription access or access outside an institution's network.

Commercial and metered adapters are called only when selected explicitly, when resolving their
own namespaced IDs, or when deliberately configured as search defaults. Setting a key alone does
not add a vendor to default searches. `list-providers` reports configuration, capabilities and
documentation links without testing access or revealing key values.

## Research workflows

Use CiteNexus to build a literature shortlist, repair an uncertain reference, check the source
behind a citation count, or prepare a bibliography for your writing tool. For a full writing
workflow, the [WTF-P companion](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/wtf-p.md) connects discovery to evidence tables, outlines
and manuscript work while keeping candidate references visible for review.

Ask your assistant to use the tools directly, or start with the `literature-review` and
`bibliography-audit` MCP prompts. Example tool arguments:

```json
{"query": "reproducible machine learning benchmarks", "providers": ["crossref", "arxiv"], "limit": 5}
```

```json
{"identifier": "10.1038/nature14539", "format": "bibtex"}
```

```json
{"citation": "10.1038/nature14539", "expected_title": "Deep learning", "expected_year": 2015}
```

```json
{"identifier": "PMID:26017442", "direction": "references", "provider": "europe_pmc", "limit": 10}
```

```json
{"identifiers": ["10.1038/nature14539", "arxiv:1706.03762"], "format": "csl-json"}
```

| Tool | Purpose |
|---|---|
| `list-providers` | Inspect source capabilities, access tiers and credential configuration |
| `search-papers` | Concurrent federated search, conservative deduplication and per-source pagination |
| `resolve-paper` | Retrieve and validate a DOI or namespaced identifier; optionally merge selected sources |
| `get-citation` | Export one resolved record as `bibtex`, `ris` or `csl-json` |
| `verify-citation` | Check an identifier or single BibTeX entry, including supplied title and year |
| `batch-citations` | Resolve and export 1–20 identifiers with ordered results, partial failures and progress |
| `related-papers` | Page through a source's citations or references |
| `paper-metrics` | Return observed citation counts, separated by provider and index |
| `find-open-access` | Find source-reported OA locations, with optional Unpaywall enrichment |
| `enhance-citation` | Normalize BibTeX formatting while preserving supplied bibliographic facts |
| `find-scholar-id` | Legacy Scholar discovery through SerpAPI; returns candidates for review |

`search-papers` defaults to 10 results **per provider**, not 10 overall. Results interleave each
provider's ranking, then merge compatible records. `limit` is 1–50, or at most 20 when using
SerpAPI. Use each provider's `next_offsets` with the **same limit**, selecting that provider for
the next call. Europe PMC search uses `next_cursors` instead: pass its token as `cursor`,
select only `europe_pmc`, keep the same query and limit, and leave `offset` at zero.
Offsets must be multiples of the limit, up to 10,000. `year_from`, `year_to` and
`open_access_only` filter the fetched page; unknown values are excluded. Abstracts are omitted
from search results by default; set `include_abstract: true` or resolve a record to retrieve them.
Provider search languages differ: explicit advanced queries use that provider's syntax.

Supported identifiers include `10.1038/nature14539`, `arxiv:1706.03762`, `PMID:26017442`,
`PMC12345`, `openalex:W2919115771`, `s2:<paperId>`, `s2:CorpusId:<number>`,
`scholar:<numericClusterId>`, `scopus:<numericId>`, and `WOS:<recordId>`. DOI, arXiv and PubMed
URLs are recognized. Arbitrary URLs are not fetched, and unprefixed numeric strings are not
assumed to be PubMed or Scholar IDs.

DOI resolution tries Crossref, DataCite and Europe PMC in order until a matching record is
retrieved. An explicit `providers` list instead checks each compatible selected source and
retains evidence and disagreements. Native identifiers route to their corresponding source.
A title search always returns candidates; it never silently declares the first result a match.

Read the MCP resources `cite-nexus://methodology`, `cite-nexus://providers` and
`cite-nexus://workflows` for machine-accessible guidance.

## What “verified” means

Verification establishes that an identifier exists in retrieved metadata and checks any supplied
title and year. It does **not** establish that a paper's findings are correct, that every author
is present, that the paper supports a specific claim, or that no retraction exists. A provider
outage produces `unavailable`, rather than a claim that the citation is fabricated.

Exports omit unavailable metadata. Partial author lists generate warnings; BibTeX uses `others`
where appropriate. Citation counts retain their source, index and observation timestamp and are
never summed across databases. Counts from different providers are not directly interchangeable.
Metadata can contain errors or conflicting publication years, and an absent retraction flag is
not proof that a paper is unretracted.

CSL-JSON is structured bibliographic data. Use a CSL processor or your reference manager to render
APA, IEEE or a journal's house style. `enhance-citation` supports `default` and `compact` formatting;
it does not infer keywords, awards, impact factors or missing authors.

## Configuration

Copy `.env.example` to `.env` only if you need optional settings. Existing process environment
variables take precedence. The CLI loads `./.env`, or an explicit `--env-file`; it never searches
parent directories. Importing the Python package does not read `.env` or call external services.
Pass `--no-env-file` for clients that manage credentials themselves. The WTF-P companion and
plugin manifests always use this mode.

| Variable | Default | Meaning |
|---|---|---|
| `CITE_NEXUS_DEFAULT_PROVIDERS` | `crossref,datacite,europe_pmc` | Explicit search source IDs, comma separated |
| `CITE_NEXUS_TIMEOUT` | `12` | Timeout in seconds for each HTTP request |
| `CITE_NEXUS_OPERATION_TIMEOUT` | `40` | Time budget for a provider operation or identifier resolution |
| `CITE_NEXUS_RETRIES` | `1` | Retries for transport failures, HTTP 429 and 5xx responses |
| `CITE_NEXUS_CONCURRENCY` | `6` | Maximum simultaneous outbound requests |
| `CITE_NEXUS_CACHE_TTL` | `300` | In-process response-cache lifetime in seconds; `0` disables it |
| `CITE_NEXUS_CACHE_SIZE` | `256` | Maximum cached responses; `0` disables caching |

Cached records retain their original retrieval and citation-observation timestamps. The cache is
bounded and partitions responses by credentials. Responses larger than 8 MB are rejected. Long
`Retry-After` cooldowns return a provider issue instead of holding the call open. Keys and upstream
error bodies are excluded from tool errors. Local stderr logging keeps stdout clean for MCP.

See [provider details](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/providers.md), [migration notes](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/migration.md), and
[product direction](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/product-direction.md) for access nuances and boundaries.

## Development and verification

To work from source:

```bash
git clone https://github.com/akougkas/cite-nexus-mcp.git
cd cite-nexus-mcp
uv sync --locked
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src/cite_nexus_mcp
uv run python scripts/prepare_release.py --check
uv run python scripts/marketplaces.py --check
uv run pytest -q
uv build
```

The automated suite uses synthetic provider fixtures and mock HTTP, plus real local stdio and
Streamable HTTP processes. It requires no vendor credentials and blocks external network access
from the test process. Paid and institutional adapters have fixture-based contract coverage;
live entitlement testing requires an account with access.

An explicit public-API smoke test is available separately:

```bash
uv run python scripts/smoke_public.py
```

It ignores account credentials and only contacts Crossref, DataCite, Europe PMC, arXiv and
anonymous Semantic Scholar. Rate limits and network failures are reported as outcomes.

The official MCP Tasks extension is not advertised. SDK 2.2 does not implement it yet.
`batch-citations` is a bounded synchronous workflow with progress and cancellation, not a durable
job queue. [The roadmap](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/product-direction.md) describes the criteria for adding persistent
tasks, local libraries and further licensed providers.

The [launch kit](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/release/launch-kit.md) includes positioning, listing copy, a demo script,
and promotional drafts. The [marketplace inventory](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/release/marketplaces.md) tracks 41
channels and leads, including verified routes, duplicate channels and inactive or unresolved
sites. Source metadata, portable plugin manifests and image assets are prepared for review.
See [data handling](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/docs/data-handling.md) before configuring optional providers or hosting.

## License

[MIT](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.0/LICENSE). Provider content, API access and redistribution remain subject to each source's terms.

<!-- mcp-name: io.github.akougkas/cite-nexus-mcp -->
