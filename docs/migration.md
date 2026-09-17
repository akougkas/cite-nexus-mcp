# Migrating from 0.1 to 0.2

Version 0.2 changes the data model and MCP implementation. The four old tool names remain, but
clients should refresh their tool schemas and consume structured output.

## Important behavior changes

| 0.1 | 0.2 |
|---|---|
| Every useful workflow required SerpAPI | Public API search and DOI resolution work without keys |
| Scholar cluster ID treated as a universal key | Namespaced DOI, arXiv, PubMed and provider IDs |
| LLM-generated BibTeX and inferred metadata | Deterministic BibTeX, RIS and CSL-JSON from observed fields |
| “Elicitation” described as an LLM formatter | Elicitation is user-input collection; no elicitation-based formatting |
| Citation sample length reported as total count | Observed counts with provider, index and timestamp |
| Text-only results and error strings | Typed structured results and proper MCP tool errors |
| `cite-paper` identity with inconsistent version | `cite-nexus`, package and server version 0.2.0 |
| SDK 1.x low-level server and stdio only | SDK 2.2 MCPServer, stdio and local Streamable HTTP |

`get-citation` and `paper-metrics` accept the old `scholar_id` argument. New calls should use
`identifier`, for example `{"identifier":"doi:10.1038/nature14539"}`. Supply exactly one of
`identifier` and `scholar_id`. `find-scholar-id` now returns candidate records rather than asserting
that its first result is the paper you intended.

`enhance-citation` accepts `default` and `compact`. Free-form model instructions no longer cause
facts to be inferred. Use `verify-citation` for identifier/title/year comparisons and a CSL
processor for a publication's rendered style.

Existing `SERP_API_KEY` and `SERPAPI_KEY` variables are aliases for `SERPAPI_API_KEY`. The latter
has precedence. The existing `.env` file can remain in place. `OPENAI_*` and `LOCAL_AI_*` variables
are not consulted by the MCP server.

The core no longer installs LiteLLM, the Google Search Results wrapper, or Requests. The old
standalone `llm_factory` Python API remains available through `uv sync --extra legacy-ai` for
existing experiments; it is not called by the MCP tools. The deprecated `elicitation` helpers
preserve queries and format metadata deterministically. `test_safe_providers.py` remains a local
manual experiment and is outside the automated suite. The old internal `ScholarAPI` class was
removed; use `ResearchService` or the `SerpAPI` provider adapter for new Python integrations.

## MCP protocol revision

The [2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
uses stateless discovery, per-request version and capability metadata, typed result discriminators,
and cache hints. SDK 2.2 handles those wire requirements and compatibility with prior protocol
revisions. The tests exercise both the current revision and the SDK's legacy handshake path over
real stdio and HTTP transports.

CiteNexus declares read-only tools, input and output schemas, stable tool ordering, private
resource-content cache hints, two prompts, and three resources. Tool exceptions become proper
MCP tool errors. Batch work reports progress and propagates cancellation.

Sampling, Roots and Logging are deprecated in the new specification; new citation workflows do
not depend on them. Logs go to stderr. The protocol's Tasks facility moved to the
[official Tasks extension](https://github.com/modelcontextprotocol/ext-tasks), which SDK 2.2
[does not yet implement](https://py.sdk.modelcontextprotocol.io/whats-new/). CiteNexus therefore
does not advertise Tasks, Apps, background jobs or durable session state.

## Python API

```python
import asyncio
from cite_nexus_mcp.config import Settings
from cite_nexus_mcp.service import ResearchService

async def main():
    service = ResearchService(Settings())
    try:
        result = await service.citation("10.1038/nature14539", "bibtex")
        print(result.citation)
        print(result.warnings)
    finally:
        await service.close()

asyncio.run(main())
```

Use `Settings.from_env()` to read process environment variables in your own application. Loading
`.env` belongs to your application entry point. Provider errors and invalid input raise exceptions;
callers should not look for an `Error:` prefix in a successful text response.
