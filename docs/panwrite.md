# PanCite + PanWrite

**PanCite finds and checks research sources. PanWrite turns research into a writing workflow.**
The companion links PanWrite's existing citation-search command to PanCite through real MCP
stdio, preserving provenance and candidate status. PanCite 0.3.0 includes the companion.
PanCite 0.3.0 speaks `pancite.panwrite/v1` and returns each source record in `pancite`. Use a
PanWrite release that selects `--backend=pancite` and reads `PANWRITE_PANCITE_COMMAND`; WTF-P
releases built for `cite-nexus.wtfp/v1` do not work with this release.

## Install the companion

```bash
uv tool install pancite==0.3.0
pancite-panwrite --check
```

Keep `pancite-panwrite` on the PATH used by PanWrite, or set `PANWRITE_PANCITE_COMMAND` to its
absolute installed path. On Windows, use the installed `pancite-panwrite.exe` path. The
companion is a separate Python installation; adding the PanWrite backend does not install it.

## Develop and verify the paired checkouts

With PanCite and [PanWrite](https://github.com/PanStudio/panwrite) checked out side by side:

```bash
cd pancite
uv sync --locked
uv run pancite-panwrite --check
uv run python scripts/check_panwrite.py --panwrite-root ../panwrite
```

The first check tests MCP startup and provider configuration without contacting a vendor.
The second exercises both generated PanWrite execution paths against fixture provider data.
It uses no account credentials and changes no user profile.

Set the companion path in the environment launching PanWrite, using your actual checkout path:

```bash
export PANWRITE_PANCITE_COMMAND=/absolute/path/to/pancite/.venv/bin/pancite-panwrite
node ../panwrite/vendors/plugin/tools/wtfp-tool.js citation-search \
  --backend=pancite --query="reproducible research" --limit=5 --timeout=30
```

The search contacts Crossref, DataCite and Europe PMC. For computer-science topics, use
`--providers=arxiv,semantic_scholar`, adding `crossref` for published versions. Optional graph, commercial and institutional providers use
the [documented credential names](providers.md) and must be selected explicitly.
The companion ignores `.env` files and `PANCITE_DEFAULT_PROVIDERS`; set optional keys in
the launching environment. Only selected providers' credentials pass through PanWrite.

## Use it in a writing workflow

Ask PanWrite to use its approved citation-search operation with `--backend=pancite` and
record the selected providers and query scope in the network approval. Preserve each result's
`pancite` source record alongside its candidate BibTeX in the research evidence table.
Review warnings and partial provider errors. Independently verify identifiers and claim
support before adopting a reference in the manuscript.

PanWrite owns bibliography files, project state and user approval. PanCite returns records
without writing to the project. A title search remains a set of candidates, even when a
provider supplies a DOI. Candidate BibTeX never adds `wtfp_status=official`. Citation counts
remain separate observations, and the backend preserves provider order rather than inventing
an impact or relevance score. Only `--intent=balanced` is supported on this backend.

The displayed result limit is 1–25 overall; native PanCite limits are per provider. Metadata
records both the fetched-page count and the displayed count. Upstream pagination information
describes provider pages; use native `search-papers` for complete paging when a displayed result
set is truncated. Per-call startup means the metadata cache is not reused between PanWrite calls.

A `pancite.panwrite/v1` request may add `detail` (`minimal`, `compact` or `full`; default `full`)
and `limit_total` (1–150). Both pass through to `search-papers` and are echoed in `metadata`.
The default keeps the full source record in each result's `pancite` field. `compact` drops
per-field provenance, and `minimal` keeps only identity fields; both leave the abstract in the
top-level `abstract` field instead of repeating it in `pancite`. `limit_total` caps records across
providers before the displayed `limit` applies:

```json
{"schema_version": "pancite.panwrite/v1", "query": "LLM multi-agent orchestration",
 "providers": ["arxiv", "semantic_scholar"], "limit": 10, "limit_total": 10, "detail": "minimal"}
```

## Host support and optional native MCP connection

PanWrite's bounded dispatcher is bound on Clio and Claude Code. Its other five host projections
retain their existing unavailable-action behavior. Shipping the helper in every generated
envelope does not certify shell execution or native MCP lifecycle on every host. Process and
integration tests qualify the paired PanWrite workflow on Linux. Installed PanCite wheel and
companion diagnostics also pass on Windows and macOS; these checks do not qualify a native
client installation or the complete PanWrite workflow on those systems.

For all 11 PanCite tools, configure PanCite directly in your MCP client using the README,
or test the [prepared companion plugin](../packaging/pancite/README.md) in a disposable
profile. That optional native connection is independent of PanWrite's search backend. It has
portable Agent Plugins 1.0 and Codex/Claude compatibility metadata, but no public listing,
hosted endpoint or client lifecycle certification is claimed.

## Failure and removal

No hidden provider fallback occurs when the selected backend fails. Check
`pancite-panwrite --check`, the executable path, selected provider configuration and
`metadata.errors`. `--offline` blocks the network operation before process launch. Requests
have bounded queries, output, nesting and timeouts; cancellation closes the MCP server.
Third-party stderr is not relayed into the workflow.

Omit `--backend=pancite` to return to PanWrite's existing backend. Unset
`PANWRITE_PANCITE_COMMAND` and remove the separately installed Python environment if desired.
No background service or registration is created by the bridge.
