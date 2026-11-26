# CiteNexus for PanCode

This pack runs the CiteNexus MCP server in PanCode. CiteNexus is licensed under Apache-2.0.

## Install

From PanHub, once the pack is listed:

```bash
pancode hub install plugin:cite-nexus
```

From a checkout of this repository:

```bash
pancode hub install <checkout>/pancode --user
```

## Approve the server

PanCode asks for two approvals. The first approves the launch; the second approves the tool
surface the server serves. Without `--hash`, the second command prints the surface digest and
records nothing; repeat it with `--hash <digest>` to record it.

```bash
pancode mcp trust cite-nexus
pancode mcp trust cite-nexus --surface
```

## The launch

`mcp.json` launches `uvx --from pancite==0.2.6 cite-nexus-mcp --no-env-file`. The
exact version pins uv's input, not the bytes PyPI serves for it. The first launch needs PyPI
to install the package into uv's cache; later launches reuse that cache. `uvx` must be on
`PATH`. `--no-env-file` keeps the server from reading a `.env` file in the pack directory.

## Action classes

Every tool is declared `read`, so lookups run without asking. No tool writes a file, takes a
file path or changes state outside the server's process: the server queries fixed scholarly
API hosts, formats BibTeX the caller supplies, reports its own provider configuration, and
caches metadata in process only. A tool a later CiteNexus release adds stays `unknown`, which
asks, until this pack lists it.

## Keys and provider terms

PanCode passes an MCP server only a safe allowlist of environment variables, so no credential
in your shell reaches this server, and the pack sets none. The free providers need no key. To
use a keyed or metered provider, write your own user-scope server declaration with the keys in
its `env`. Choosing such a provider accepts that provider's terms; see
[providers](https://github.com/PanStudio/pancite/blob/v0.2.6/docs/providers.md).

## Network

Every lookup needs network. Inside a PanCode fleet worker the server reaches the network only
after `pancode mcp trust cite-nexus --network`.

## The literature pack

PanCode's first-party literature pack declares the same server id, `cite-nexus`. Install one of
the two; when both declare the server, the second is shadowed.
