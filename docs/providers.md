# Provider contracts and access

CiteNexus uses documented APIs through a common asynchronous HTTP client. Provider terms, quotas,
coverage and account entitlements can change independently of a CiteNexus release. Documentation
and public API behavior were checked on **2026-09-16**. No paid or institutional account was used
to validate this upgrade.

## Open metadata

**[Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)** is the first
choice for publisher-deposited DOI metadata. CiteNexus uses bibliographic search and exact DOI
lookup, with optional `mailto` polite-pool identification. Citation counts are the provider's
`is-referenced-by-count`. Not every record includes an abstract, references, authors or complete
publication details. A retraction notice linked through `update-to` is not the same as a complete
retraction check of the target paper.

**[DataCite](https://support.datacite.org/docs/api)** complements Crossref with datasets, software,
repository deposits and other research outputs. Both are searched by default, and DOI resolution
falls back from Crossref to DataCite. Versioned and unversioned dataset DOIs remain distinct.
Search is page based; retain the same page size while following offsets.

## Academic and subject-specific sources

**[Europe PMC](https://europepmc.org/RestfulWebService)** supplies biomedical metadata, including
PubMed and PMC identifiers. This adapter uses Europe PMC's API; it does not claim to be a direct
NCBI E-utilities adapter. Search and lookup request core metadata. Search uses native `cursorMark` pagination (the API
ignores numeric page arguments); `next_cursors` supplies the token for the next request. Citation/reference graph pages
may contain less metadata than full records. A PMC ID alone does not imply an open license.
Use native syntax such as `TITLE:"deep learning"`, `AUTH_LAST:LeCun` or `DOI:10.1038/nature14539`.

**[arXiv](https://info.arxiv.org/help/api/user-manual.html)** supplies Atom records. Requests are
paced at least three seconds apart within one server process; multiple instances need coordinated
rate limiting. arXiv versions normalize to the base arXiv identifier for discovery. The preprint
record remains distinguished from a known published record, even when it reports the publication's
DOI. Revision-specific preservation is a future feature. Native fields such as `ti:`, `au:` and
`cat:` are accepted. A bare query becomes an `all:` search.

**[Semantic Scholar](https://api.semanticscholar.org/api-docs/graph)** supports search, exact record
lookup, citations and references. Anonymous access has shared limits and can return 429 frequently;
a key may improve reliability, subject to the provider's policy. CiteNexus requests one API call
per second per process. `citingPaper` and `citedPaper` are mapped separately. Graph pages are never
used as a surrogate for `citationCount`.

**[OpenAlex](https://developers.openalex.org/)** supplies multidisciplinary metadata, citation
counts, OA locations and graph filters. CiteNexus requires `OPENALEX_API_KEY` and labels the adapter
as free credits / metered access. It does not treat successful anonymous requests as a durable
access guarantee or hardcode a free credit allowance. Work, DOI and PubMed lookups are supported.

## Commercial and institutional sources

**[SerpAPI Google Scholar](https://serpapi.com/google-scholar-api)** is explicitly selected through
`serpapi`, the legacy `find-scholar-id`, or a `scholar:` identifier. Its numeric cluster IDs are
local to Google Scholar, not universal research identifiers. Result IDs are not cluster IDs.
Citation counts come from `inline_links.cited_by.total`; search snippets are never relabeled as
abstracts, and author lists are marked incomplete. The adapter supports up to 20 results per page
and citation traversal, but does not expose a reference-list operation. This is a vendor integration,
not a Google-supported Scholar API.

**[Elsevier Scopus](https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl)** uses the search
API with `X-ELS-APIKey` and optional `X-ELS-Insttoken`. Institutional network location, subscription
and key scope may determine availability. The STANDARD view can contain only a lead author, which
CiteNexus marks as incomplete. Plain text is wrapped in `TITLE-ABS-KEY(...)`; advanced Scopus queries are preserved, for example
`TITLE-ABS-KEY("reproducible research")`. Exact DOI and Scopus ID lookup use constrained search
queries, and the returned ID is checked. Abstract retrieval, author profiles and graph traversal
are not advertised by this adapter.

**[Web of Science Starter](https://developer.clarivate.com/apis/wos-starter)** uses the documented
v1 document endpoint and `X-ApiKey`. Plain text is wrapped in `TS=(...)`; advanced queries such as `TS=("reproducible research")` are preserved. Counts retain
the reported collection abbreviation and may be absent depending on the subscription. CiteNexus
does not claim the capabilities of Web of Science Expanded or the Journals API.

## Open-access enrichment

**[Unpaywall](https://unpaywall.org/products/api)** is a DOI enrichment service, not a search
provider. Set `UNPAYWALL_EMAIL` to enable it in `find-open-access`. Locations retain the source's
license and manuscript version. CiteNexus returns URLs; it makes no arbitrary outbound request to
a publisher, repository or user-supplied URL. Without Unpaywall, default DOI workflows also check
Europe PMC for reported open-access locations.

## Failure and result policy

- A missing credential becomes `not_configured` before sending a request.
- 401/403 becomes `access_denied`; 429 becomes `rate_limited` with a cooldown when supplied.
- Timeout, transport, malformed response and missing-record outcomes remain distinct.
- Federated search returns usable results plus provider issues. All-provider failure is an MCP
  tool error, rather than a successful empty literature search.
- Exact lookup rejects a missing or mismatched requested identifier.
- Provider payloads are not instructions. Error responses do not expose vendor bodies or keys.
- Field attribution records where retained values originated. It is not a field-confidence score;
  metadata is not ranked by an invented universal authority hierarchy.

The native response fixtures cover request parameters, parsing and representative failure behavior.
Live tests with licensed accounts should be run before relying on a commercial adapter in a
production institutional deployment.
