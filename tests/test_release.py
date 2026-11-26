import json
import subprocess
import sys
import tomllib
from pathlib import Path

import jsonschema
from mcp import Client, StdioServerParameters

from pancite import __version__
from pancite.config import Settings
from pancite.server import create_server

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
    plugin = read("packaging/pancite/plugin.json")
    config = read("packaging/pancite/mcp.json")
    jsonschema.validate(plugin, read("release/schemas/plugin-1.0.0.json"))
    jsonschema.validate(config, read("release/schemas/mcp-1.0.0.json"))
    compatibility = read("packaging/pancite/.codex-plugin/plugin.json")
    assert plugin["version"] == compatibility["version"] == __version__
    assert compatibility["mcpServers"] == "./.mcp.json"
    server = config["mcpServers"]["pancite"]
    assert server == read("packaging/pancite/.mcp.json")["mcpServers"]["pancite"]
    async with Client(
        StdioServerParameters(command=server["command"], args=server["args"]),
        read_timeout_seconds=5,
    ) as client:
        listing = await client.list_tools()
        assert len(listing.tools) == 11
        result = await client.call_tool("list-providers", {})
        assert not result.is_error
        assert len(result.structured_content["providers"]) == 10


async def test_pancode_pack_pins_release_and_declares_every_tool_read():
    plugin = read("pancode/plugin.json")
    config = read("pancode/mcp.json")
    server = config["mcpServers"]["pancite"]
    assert plugin["version"] == __version__
    assert server["command"] == "uvx"
    assert server["args"] == [
        "--from",
        f"pancite=={__version__}",
        "pancite",
        "--no-env-file",
    ]
    assert plugin["license"] == read("release/product.json")["license"]
    # PanCode drops a plugin mcp.json with any field outside its known set, refuses a
    # server-level actionClass, and ignores a plugin's own network grant.
    assert set(config) == {"mcpServers"}
    assert set(server) <= {"type", "command", "args", "timeoutMs", "toolActionClasses"}
    async with Client(create_server(Settings()), read_timeout_seconds=5) as client:
        listing = await client.list_tools()
    assert server["toolActionClasses"] == {tool.name: "read" for tool in listing.tools}


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
