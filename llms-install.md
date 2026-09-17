# Installing the prepared CiteNexus checkout

This is installation guidance, not permission to change a user's client configuration.
Use the user's chosen scope and the client's supported configuration mechanism.
Version 0.2.0 is unreleased; do not substitute an older PyPI package for this checkout.

1. Check Python 3.11+ and uv are available.
2. In this repository, run `uv sync --locked`.
3. Run `uv run cite-nexus-mcp --version` and `uv run cite-nexus-mcp --no-env-file --list-providers`.
4. Configure an MCP stdio connection with executable `uv` and separate arguments
   `--directory`, the absolute repository path, `run`, `--locked`, `cite-nexus-mcp`,
   `--no-env-file`. Use an absolute uv executable path if the client has a restricted PATH.
5. Restart that connection, list tools, and call `list-providers`. Expect 11 tools and nine
   provider entries. No API key is required and no provider call is needed for this check.
6. With the user's intended network scope, try `search-papers` using a public topic,
   `providers: ["crossref"]`, and `limit: 3`. Inspect partial errors and source records.

Commercial and metered sources require explicit selection plus optional account setup.
Do not create or print credentials. Do not activate every provider simply because a key
exists. This stdio setup needs no public port. See `docs/wtf-p.md` for the separate
companion; it does not install or register an MCP connection automatically.
