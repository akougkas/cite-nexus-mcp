# Installing CiteNexus 0.2.1

This is installation guidance, not permission to change a user's client configuration.
Use the user's chosen scope and the client's supported configuration mechanism.
Use the pinned `cite-nexus-mcp==0.2.1` package from PyPI.

1. Check Python 3.11+ and uv are available.
2. Run `uvx --from cite-nexus-mcp==0.2.1 cite-nexus-mcp --version`.
3. Run `uvx --from cite-nexus-mcp==0.2.1 cite-nexus-mcp --no-env-file --list-providers`.
4. Configure an MCP stdio connection with executable `uvx` and separate arguments
   `--from`, `cite-nexus-mcp==0.2.1`, `cite-nexus-mcp`, `--no-env-file`.
   Use an absolute uvx executable path if the client has a restricted PATH.
5. Restart that connection, list tools, and call `list-providers`. Expect 11 tools and nine
   provider entries. No API key is required and no provider call is needed for this check.
6. With the user's intended network scope, try `search-papers` using a public topic,
   `providers: ["crossref"]`, and `limit: 3`. Inspect partial errors and source records.

Commercial and metered sources require explicit selection plus optional account setup.
Do not create or print credentials. Do not activate every provider simply because a key
exists. This stdio setup needs no public port. See `docs/wtf-p.md` for the separate
companion; it does not install or register an MCP connection automatically.
