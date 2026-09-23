# CiteNexus 0.2.3

Release date: 2026-09-23. Source: annotated tag `v0.2.3`.

This release introduces native support for SearchApi.io as a cost-effective alternative commercial provider for Google Scholar discovery, identifier resolution, and citation graph traversal. SerpAPI remains fully supported with zero breaking changes.

## New Features

- **SearchApi.io Google Scholar Provider (`searchapi`):**
  - Integrated via `https://www.searchapi.io/api/v1/search` using the `google_scholar` engine.
  - Offers a significantly lower cost structure (~$4/1k searches on the Developer tier vs. ~$15–$25/1k on SerpAPI) while maintaining 1:1 functional parity for academic queries (`q`), cluster lookups (`cluster`), and citation traversals (`cites`).
- **Smart Scholar Routing & Automatic Resolution:**
  - `scholar:<cluster_id>` identifiers now automatically route through `searchapi` when `SEARCHAPI_API_KEY` is configured, falling back to `serpapi` if `SERPAPI_API_KEY` is configured.
  - Legacy discovery tools (`find-scholar-id`, `get-citation`, `paper-metrics`) dynamically utilize whichever Google Scholar provider is active.
- **Unified Google Scholar Parser:**
  - `SerpAPI` and `SearchAPI` share a resilient normalization pipeline that handles root-level author lists, publication summaries, `data_cid` cluster identifiers, and pagination formats seamlessly.
- **Subprocess Bridge & Client Manifests:**
  - `cite-nexus-wtfp` forwards `SEARCHAPI_API_KEY` to child stdio processes and includes `searchapi` in its validated provider schema.
  - Registry manifest (`server.json`) and Agent Plugin descriptors declare `SEARCHAPI_API_KEY` as an optional secret.

## Install

```bash
uvx --from cite-nexus-mcp==0.2.3 cite-nexus-mcp --no-env-file
uvx --from cite-nexus-mcp==0.2.3 cite-nexus-wtfp --check
```

See the [changelog](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.3/CHANGELOG.md) and [documentation](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.3/README.md) for further details.
