"""Generate local registry/plugin metadata. Never installs, publishes or submits."""

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def outputs() -> dict[str, str]:
    product = json.loads((ROOT / "release/product.json").read_text())
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    server = {"command": "cite-nexus-mcp", "args": ["--no-env-file"]}
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
        "CITE_NEXUS_CONTACT_EMAIL": (False, "Optional Crossref polite-pool contact email"),
        "SEMANTIC_SCHOLAR_API_KEY": (True, "Optional Semantic Scholar account key"),
        "OPENALEX_API_KEY": (
            True,
            "Key for explicitly selected OpenAlex queries; account credits apply",
        ),
        "SERPAPI_API_KEY": (True, "Key for explicitly selected commercial Google Scholar queries"),
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
                    "identifier": "cite-nexus-mcp",
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
        "packaging/cite-nexus/plugin.json": {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            **common,
            "extensions": {"com.openai": {"interface": interface}},
        },
        "packaging/cite-nexus/mcp.json": {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {"cite-nexus": {"type": "stdio", **server}},
        },
        "packaging/cite-nexus/.codex-plugin/plugin.json": {
            **common,
            "mcpServers": "./.mcp.json",
            "interface": interface,
        },
        "packaging/cite-nexus/.claude-plugin/plugin.json": common,
        "packaging/cite-nexus/.mcp.json": {
            "mcpServers": {"cite-nexus": {"type": "stdio", **server}}
        },
    }
    rendered = {
        path: json.dumps(data, indent=2, ensure_ascii=False) + "\n" for path, data in files.items()
    }
    rendered["packaging/cite-nexus/assets/logo.svg"] = (ROOT / "assets/cite-nexus.svg").read_text()
    rendered["packaging/cite-nexus/LICENSE"] = (ROOT / "LICENSE").read_text()
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
