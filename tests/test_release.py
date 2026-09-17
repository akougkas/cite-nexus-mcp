import json
import subprocess
import sys
import tomllib
from pathlib import Path

import jsonschema
from mcp import Client, StdioServerParameters

from cite_nexus_mcp import __version__

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def test_registry_identity_schema_and_pypi_ownership_marker():
    manifest = read("server.json")
    jsonschema.validate(manifest, read("release/schemas/server-2025-12-11.json"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert manifest["version"] == project["version"] == __version__
    package = manifest["packages"][0]
    assert package["version"] == __version__
    assert package["identifier"] == project["name"]
    assert f"<!-- mcp-name: {manifest['name']} -->" in (ROOT / "README.md").read_text()
    assert not any(e["isRequired"] for e in package["environmentVariables"])


async def test_portable_plugin_schema_and_actual_connection():
    plugin = read("packaging/cite-nexus/plugin.json")
    config = read("packaging/cite-nexus/mcp.json")
    jsonschema.validate(plugin, read("release/schemas/plugin-1.0.0.json"))
    jsonschema.validate(config, read("release/schemas/mcp-1.0.0.json"))
    compatibility = read("packaging/cite-nexus/.codex-plugin/plugin.json")
    assert plugin["version"] == compatibility["version"] == __version__
    assert compatibility["mcpServers"] == "./.mcp.json"
    server = config["mcpServers"]["cite-nexus"]
    assert server == read("packaging/cite-nexus/.mcp.json")["mcpServers"]["cite-nexus"]
    async with Client(
        StdioServerParameters(command=server["command"], args=server["args"]),
        read_timeout_seconds=5,
    ) as client:
        listing = await client.list_tools()
        assert len(listing.tools) == 11
        result = await client.call_tool("list-providers", {})
        assert not result.is_error
        assert len(result.structured_content["providers"]) == 9


def test_generated_release_metadata_and_inventory_are_current():
    for script in ("prepare_release.py", "marketplaces.py"):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    data = read("release/marketplaces.json")
    entries = data["entries"]
    assert len({e["id"] for e in entries}) == len(entries)
    assert all(e["evidence_urls"] and e["next_step"] for e in entries)
    assert all(
        e["status"] in {"not_submitted", "submitted", "listed", "declined", "deferred"}
        for e in entries
    )
