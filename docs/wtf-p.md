# CiteNexus + WTF-P

**CiteNexus finds and checks research sources. WTF-P turns research into a writing workflow.**
The companion links WTF-P's existing citation-search command to CiteNexus through real MCP
stdio, preserving provenance and candidate status. CiteNexus 0.2.1 includes the companion.
The WTF-P team is preparing its matching **0.7.0** release; `wtf-p@0.6.0` does not include
the backend. Use their integration branch until that separate release is available.

## Install the companion

```bash
uv tool install cite-nexus-mcp==0.2.1
cite-nexus-wtfp --check
```

Keep `cite-nexus-wtfp` on the PATH used by WTF-P, or set `WTFP_CITE_NEXUS_COMMAND` to its
absolute installed path. On Windows, use the installed `cite-nexus-wtfp.exe` path. The
companion is a separate Python installation; adding the WTF-P backend does not install it.
Wait for WTF-P 0.7.0 or use the team's integration branch to select `--backend=cite-nexus`.

## Develop and verify the paired checkouts

With CiteNexus and [WTF-P](https://github.com/akougkas/wtf-p) checked out side by side:

```bash
cd cite-nexus-mcp
uv sync --locked
uv run cite-nexus-wtfp --check
uv run python scripts/check_wtfp.py --wtfp-root ../wtf-p
```

The first check tests MCP startup and provider configuration without contacting a vendor.
The second exercises both generated WTF-P execution paths against fixture provider data.
It uses no account credentials and changes no user profile.

Set the companion path in the environment launching WTF-P, using your actual checkout path:

```bash
export WTFP_CITE_NEXUS_COMMAND=/absolute/path/to/cite-nexus-mcp/.venv/bin/cite-nexus-wtfp
node ../wtf-p/vendors/plugin/tools/wtfp-tool.js citation-search \
  --backend=cite-nexus --query="reproducible research" --limit=5 --timeout=30
```

The search contacts Crossref, DataCite and Europe PMC. For computing preprints, add
`--providers=crossref,arxiv`. Optional graph, commercial and institutional providers use
the [documented credential names](providers.md) and must be selected explicitly.
The companion ignores `.env` files and `CITE_NEXUS_DEFAULT_PROVIDERS`; set optional keys in
the launching environment. Only selected providers' credentials pass through WTF-P.

## Use it in a writing workflow

Ask WTF-P to use its approved citation-search operation with `--backend=cite-nexus` and
record the selected providers and query scope in the network approval. Preserve each result's
`citeNexus` source record alongside its candidate BibTeX in the research evidence table.
Review warnings and partial provider errors. Independently verify identifiers and claim
support before adopting a reference in the manuscript.

WTF-P owns bibliography files, project state and user approval. CiteNexus returns records
without writing to the project. A title search remains a set of candidates, even when a
provider supplies a DOI. Candidate BibTeX never adds `wtfp_status=official`. Citation counts
remain separate observations, and the backend preserves provider order rather than inventing
an impact or relevance score. Only `--intent=balanced` is supported on this backend.

The displayed result limit is 1–25 overall; native CiteNexus limits are per provider. Metadata
records both the fetched-page count and the displayed count. Upstream pagination information
describes provider pages; use native `search-papers` for complete paging when a displayed result
set is truncated. Per-call startup means the metadata cache is not reused between WTF-P calls.

## Host support and optional native MCP connection

WTF-P's bounded dispatcher is bound on Clio and Claude Code. Its other five host projections
retain their existing unavailable-action behavior. Shipping the helper in every generated
envelope does not certify shell execution or native MCP lifecycle on every host. Process and
integration tests qualify the paired WTF-P workflow on Linux. Installed CiteNexus wheel and
companion diagnostics also pass on Windows and macOS; these checks do not qualify a native
client installation or the complete WTF-P workflow on those systems.

For all 11 CiteNexus tools, configure CiteNexus directly in your MCP client using the README,
or test the [prepared companion plugin](../packaging/cite-nexus/README.md) in a disposable
profile. That optional native connection is independent of WTF-P's search backend. It has
portable Agent Plugins 1.0 and Codex/Claude compatibility metadata, but no public listing,
hosted endpoint or client lifecycle certification is claimed.

## Failure and removal

No hidden provider fallback occurs when the selected backend fails. Check
`cite-nexus-wtfp --check`, the executable path, selected provider configuration and
`metadata.errors`. `--offline` blocks the network operation before process launch. Requests
have bounded queries, output, nesting and timeouts; cancellation closes the MCP server.
Third-party stderr is not relayed into the workflow.

Omit `--backend=cite-nexus` to return to WTF-P's existing backend. Unset
`WTFP_CITE_NEXUS_COMMAND` and remove the separately installed Python environment if desired.
No background service or registration is created by the bridge.
