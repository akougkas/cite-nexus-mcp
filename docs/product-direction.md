# Product direction

## Position

CiteNexus is the scholarly evidence service inside a research assistant. Its value is connecting
sources with different coverage, preserving what each source actually reports, and making that
evidence available in a consistent MCP interface.

The initial audience is researchers writing papers, research software engineers building agent
workflows, and university teams that already have access to licensed indexes. A useful public
API experience comes first. Institutions can add existing subscriptions without replacing the
core workflow or forcing every user into a paid search vendor.

| Need | CiteNexus's role | Complementary tool |
|---|---|---|
| Find and identify research | Search multiple sources and resolve namespaced IDs | Provider search interfaces for source-specific exploration |
| Produce a bibliography | Deterministic export with incomplete-field warnings | Zotero or another reference manager for library organization and styles |
| Audit references | Identifier/title/year verification, explicit uncertainty | Human review and publisher records for final publication checks |
| Inspect influence | Source-specific counts and citation/reference traversal | Specialist bibliometric tools and domain judgment |
| Support a literature review | Traceable queries, records, sources and workflow prompts | Full-text reading and formal review methodology |
| Turn research into a paper | Candidate discovery with source records through the optional companion | WTF-P for author decisions, evidence tables, outlines, drafting and review |

The promise is inspectable metadata and predictable behavior. Avoid claims of “perfect citations,”
“universal Scholar IDs,” proof that a paper is unretracted, or scientific truth verified from
metadata. Coverage, licensing and source differences should be visible to both the assistant and
the researcher.

## Prepared for 0.2 (unreleased)

Nine search adapters; optional Unpaywall DOI enrichment; identifier resolution; conservative
version-aware deduplication; deterministic exports; reference verification; bounded batch export;
source-specific metrics; citation/reference paging; current MCP support with backward compatibility;
a credential-free default; documented provider boundaries; and an offline regression suite.
The WTF-P companion adds a tested MCP process boundary to its existing citation-search
command. The release kit includes registry/plugin metadata, a researched distribution queue,
installation guidance and launch assets; it does not publish or register anything.

The live public-API smoke check demonstrated Crossref, DataCite, Europe PMC and arXiv search.
Anonymous Semantic Scholar returned a rate limit. Licensed adapters were checked against documented
contracts and synthetic fixtures; their real account entitlements remain untested.

## Immediate release focus

Finish a reliable first-use experience before expanding the tool catalog: clean installed
artifacts, one useful free-source search, an inspectable reference check, and the paired WTF-P
workflow. Qualify actual client installations and OS behavior before making compatibility
claims. Launch through a small verified set of registries and research communities, then
use reported coverage gaps and unresolved references to choose the next investments.

Keep native desktop/plugin packaging and a future hosted institutional service as separate
deliverables. Each has different lifecycle, authentication and support requirements. The
[release checklist](release/README.md) records those gates and the deferred marketplace routes.

## Next release priorities and acceptance criteria

1. **Complete publication integrity checks.** Integrate a documented, licensed source of retraction
   and correction relationships. Preserve notices separately from target records and expose coverage
   and observation time. Never infer “not retracted” from a missing result.
2. **Stronger bibliography reconciliation.** Compare complete author lists, venue, DOI version and
   publication dates; report proposed corrections with source-level evidence. Add round-trip fixtures
   from real reference managers and a CSL rendering layer with pinned styles if demand warrants it.
3. **Durable research batches.** Adopt the official MCP Tasks extension once a supported implementation
   is available. Require persistent task storage, bounded quotas, ownership checks, TTL cleanup,
   cooperative cancellation, reconnect tests and explicit behavior for provider charges on retries.
   A process-local task dictionary is not sufficient for this promise.
4. **Local reference-manager integration.** Start with explicit BibTeX/RIS/CSL import/export and then
   optional Zotero integration. Preserve library provenance and support idempotent updates and
   conflict review before adding automatic synchronization.
5. **Institution deployments.** Add standard MCP authorization and per-user provider credentials,
   shared quota management and observable provider health. Validate with actual Scopus and Web of
   Science subscriptions before describing the deployment as institution-ready.
6. **Expand specialized coverage on demonstrated need.** Evaluate direct NCBI E-utilities for
   controlled biomedical queries, NASA ADS for astronomy, IEEE Xplore for engineering, OpenAIRE/CORE
   for repositories and publisher text-mining APIs for entitled full text. Each adapter must have
   documented terms, credential isolation, fixtures, native identifier support, bounded requests,
   pagination tests and a truthful capability declaration.

A richer visual interface or MCP App can follow when it improves a concrete workflow, such as
comparing candidate matches or reviewing proposed bibliography corrections. The headless research
service remains independently useful.

## Quality measures

Track exact identifier resolution success, verified-field mismatch rates, author-list completeness,
provider-specific latency and rate limits, cost per completed workflow, and unresolved bibliography
entries. Test false merges across preprints and published versions. Keep live provider availability
separate from offline contract-test coverage. These measures are more useful than a raw tool count.
