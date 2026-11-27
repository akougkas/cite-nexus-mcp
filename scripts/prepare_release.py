"""Generate local registry/plugin metadata. Never installs, publishes or submits."""

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Every tool the server registers. A tool a later release adds stays `unknown` in PanCode,
# which asks before each call, until it is listed here.
PANCODE_READ_TOOLS = (
    "batch-citations",
    "enhance-citation",
    "find-open-access",
    "find-scholar-id",
    "get-citation",
    "list-providers",
    "paper-metrics",
    "related-papers",
    "resolve-paper",
    "search-papers",
    "verify-citation",
)

PANCODE_README = """\
# PanCite for PanCode

This pack runs the PanCite MCP server in PanCode. PanCite is licensed under Apache-2.0.

## Install

From PanHub, once the pack is listed:

```bash
pancode hub install plugin:pancite
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
pancode mcp trust pancite
pancode mcp trust pancite --surface
```

## The launch

`mcp.json` launches `uvx --from pancite=={version} pancite --no-env-file`. The
exact version pins uv's input, not the bytes PyPI serves for it. The first launch needs PyPI
to install the package into uv's cache; later launches reuse that cache. `uvx` must be on
`PATH`. The server reads only its process environment and never a `.env` file in the
pack directory.

## Action classes

Every tool is declared `read`, so lookups run without asking. No tool writes a file, takes a
file path or changes state outside the server's process: the server queries fixed scholarly
API hosts, formats BibTeX the caller supplies, reports its own provider configuration, and
caches metadata in process only. A tool a later PanCite release adds stays `unknown`, which
asks, until this pack lists it.

## Keys and provider terms

PanCode passes an MCP server only a safe allowlist of environment variables, so no credential
in your shell reaches this server, and the pack sets none. The free providers need no key. To
use a keyed or metered provider, write your own user-scope server declaration with the keys in
its `env`. Choosing such a provider accepts that provider's terms; see
[providers](https://github.com/PanStudio/pancite/blob/v{version}/docs/providers.md).

## Network

Every lookup needs network. Inside a PanCode fleet worker the server reaches the network only
after `pancode mcp trust pancite --network`.

## The literature pack

PanCode's first-party literature pack declares this server under its former id, `cite-nexus`.
Install one of the two packs; with both installed, PanCode starts two copies of the server.
"""


def outputs() -> dict[str, str]:
    product = json.loads((ROOT / "release/product.json").read_text())
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    server = {"command": "pancite", "args": ["--no-env-file"]}
    interface = {
        "displayName": product["name"],
        "shortDescription": product["short_description"],
        "longDescription": product["description"],
        "developerName": product["author"]["name"],
        "category": "Productivity",
        "capabilities": ["Read"],
        "websiteURL": product["repository"],
        "brandColor": "#145C53",
        "logo": "./assets/logo.svg",
        "defaultPrompt": "Search free scholarly sources for my topic, retain source evidence, and verify identifiers before exporting citations.",
    }
    common = {
        "name": product["slug"],
        "version": version,
        "description": product["description"],
        "author": product["author"],
        "homepage": product["repository"],
        "repository": product["repository"],
        "license": product["license"],
        "keywords": product["keywords"],
    }
    optional = {
        "PANCITE_CONTACT_EMAIL": (False, "Optional Crossref polite-pool contact email"),
        "SEMANTIC_SCHOLAR_API_KEY": (True, "Optional Semantic Scholar account key"),
        "OPENALEX_API_KEY": (
            True,
            "Key for explicitly selected OpenAlex queries; account credits apply",
        ),
        "SERPAPI_API_KEY": (True, "Key for explicitly selected commercial Google Scholar queries"),
        "SEARCHAPI_API_KEY": (
            True,
            "Key for explicitly selected commercial Google Scholar queries via SearchApi.io",
        ),
        "SCOPUS_API_KEY": (
            True,
            "Key for explicitly selected Scopus queries; entitlement required",
        ),
        "SCOPUS_INSTTOKEN": (True, "Optional Scopus institutional token"),
        "WOS_API_KEY": (True, "Key for explicitly selected Web of Science Starter queries"),
        "UNPAYWALL_EMAIL": (False, "Optional email for Unpaywall open-access enrichment"),
    }
    files = {
        "server.json": {
            "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
            "name": product["registry_name"],
            "title": product["name"],
            "description": product["short_description"],
            "version": version,
            "repository": {"url": product["repository"], "source": "github"},
            "websiteUrl": product["repository"],
            "packages": [
                {
                    "registryType": "pypi",
                    "identifier": "pancite",
                    "version": version,
                    "runtimeHint": "uvx",
                    "transport": {"type": "stdio"},
                    "packageArguments": [{"type": "named", "name": "--no-env-file"}],
                    "environmentVariables": [
                        {
                            "name": name,
                            "description": description,
                            "isRequired": False,
                            "isSecret": secret,
                            "format": "string",
                        }
                        for name, (secret, description) in optional.items()
                    ],
                }
            ],
        },
        "packaging/pancite/plugin.json": {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            **common,
            "extensions": {"com.openai": {"interface": interface}},
        },
        "packaging/pancite/mcp.json": {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"pancite": {"type": "stdio", **server}},
        },
        "packaging/pancite/.codex-plugin/plugin.json": {
            **common,
            "mcpServers": "./.mcp.json",
            "interface": interface,
        },
        "packaging/pancite/.claude-plugin/plugin.json": common,
        "packaging/pancite/.mcp.json": {"mcpServers": {"pancite": {"type": "stdio", **server}}},
        "pancode/plugin.json": {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            **common,
            "extensions": {
                "dev.pancode": {
                    "manifestVersion": 1,
                    "compatibility": {"pancode": ">=0.9.0-0"},
                }
            },
        },
        # PanCode's plugin fields (timeoutMs, toolActionClasses) are outside the Agent Plugins
        # schema, so this file carries no $schema.
        "pancode/mcp.json": {
            "mcpServers": {
                "pancite": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": [
                        "--from",
                        f"pancite=={version}",
                        "pancite",
                        "--no-env-file",
                    ],
                    "timeoutMs": 120000,
                    "toolActionClasses": {tool: "read" for tool in PANCODE_READ_TOOLS},
                }
            }
        },
    }
    rendered = {
        path: json.dumps(data, indent=2, ensure_ascii=False) + "\n" for path, data in files.items()
    }
    rendered["packaging/pancite/assets/logo.svg"] = (ROOT / "assets/pancite.svg").read_text()
    rendered["packaging/pancite/LICENSE"] = (ROOT / "LICENSE").read_text()
    rendered["packaging/pancite/NOTICE"] = (ROOT / "NOTICE").read_text()
    rendered["pancode/LICENSE"] = (ROOT / "LICENSE").read_text()
    rendered["pancode/NOTICE"] = (ROOT / "NOTICE").read_text()
    rendered["pancode/README.md"] = PANCODE_README.format(version=version)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without writing files")
    args = parser.parse_args()
    drift = []
    for relative, content in outputs().items():
        path = ROOT / relative
        if path.exists() and path.read_text() == content:
            continue
        drift.append(relative)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if args.check and drift:
        raise SystemExit("Release metadata drift: " + ", ".join(drift))
    print(
        f"Release metadata {'checked' if args.check else 'prepared'} locally; {len(drift)} changed files; nothing published."
    )


if __name__ == "__main__":
    main()
