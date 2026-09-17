# Contributing

Install development dependencies with `uv sync --locked`. Before submitting changes, run the lint,
type, test and build commands in the README. Tests must not require network access or account keys.
Use `scripts/smoke_public.py` separately for explicit public API checks.

## Architecture

- `config.py` reads explicit settings; only the CLI loads `.env`.
- `http.py` owns request limits, retries, pacing, response-size bounds, caching and sanitized failures.
- `providers/` contains source-specific endpoints and normalization.
- `models.py` defines public records and structured tool outputs.
- `identifiers.py` parses namespaced identifiers without fetching arbitrary URLs.
- `service.py` coordinates search, identity checks, source merging and research workflows.
- `citations.py` formats observed metadata without a language model.
- `server.py` exposes typed MCP tools, resources and prompts and manages the service lifecycle.

Keep source-specific API behavior in its adapter. Changes to the research service should remain
independent of MCP client implementation or transport. Keep output schemas accurate and preserve
error distinctions; clients depend on the difference between no result and an unavailable source.

## Adding a source

Document the API's access tier, terms, authentication, request limits and paging model first.
Implement the `Provider` interface, use the shared HTTP layer, and add it to the registry. A provider
must declare only the operations it implements. Commercial access must be explicitly selected or
configured as a default; setting credentials alone must not introduce automatic charges.

Normalize native IDs, preserve provider URLs and counts, and identify incomplete author lists.
Never map a snippet to a full abstract or a partial graph page to a citation total. Do not fabricate
metadata to fill a schema. Search results may be candidates; exact resolution must verify the
requested identifier against the returned record.

Add realistic, non-sensitive fixtures for search, lookup and any supported graph operations.
Cover pagination, missing values, auth/rate-limit failures and malformed records. Add a live check
only as an explicit opt-in script, and distinguish fixture coverage from live account validation
in the documentation. Avoid storing licensed payloads without redistribution permission.

## Releases

Keep the version in `pyproject.toml` and `cite_nexus_mcp.__version__` aligned, refresh `uv.lock`, and
build both artifacts with `uv build`. Verify that the wheel and source archive contain no `.env`,
credentials, local assistant configuration or manual user experiments. Validate an installed wheel
outside the repository before publishing. The local HTTP CLI is not a multi-user deployment layer.
