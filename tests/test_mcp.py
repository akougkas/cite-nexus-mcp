import asyncio
import json
import os
import socket
import subprocess
import sys

import httpx2 as httpx
import jsonschema
import pytest
from mcp import Client, StdioServerParameters

from cite_nexus_mcp.config import Settings
from cite_nexus_mcp.http import HTTP
from cite_nexus_mcp.server import create_server
from cite_nexus_mcp.service import ResearchService


@pytest.mark.parametrize("mode", ["2026-07-28", "legacy"])
async def test_protocol_schemas_resources_prompts_and_errors(mode, records):
    def handler(_):
        return httpx.Response(200, json={"message": records["crossref"]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(
            create_server(service=service), mode=mode, read_timeout_seconds=5
        ) as client:
            result = await client.list_tools()
            names = [tool.name for tool in result.tools]
            assert names == sorted(names)
            assert len(names) == 11
            for tool in result.tools:
                assert tool.annotations.read_only_hint
                assert tool.output_schema
                jsonschema.Draft202012Validator.check_schema(tool.input_schema)
                jsonschema.Draft202012Validator.check_schema(tool.output_schema)
            exported = await client.call_tool("get-citation", {"identifier": "10.1234/example"})
            assert not exported.is_error
            assert exported.structured_content["paper"]["title"] == "Reliable Research & Data"
            tool = next(t for t in result.tools if t.name == "get-citation")
            jsonschema.validate(exported.structured_content, tool.output_schema)
            for name, arguments in [
                ("search-papers", {"query": "q", "limit": 0}),
                ("get-citation", {}),
                ("resolve-paper", {"identifier": "not an id"}),
                ("enhance-citation", {"bibtex": "invalid"}),
            ]:
                failed = await client.call_tool(name, arguments)
                assert failed.is_error, name
            resources = await client.list_resources()
            assert len(resources.resources) == 3
            methodology = await client.read_resource("cite-nexus://methodology")
            assert "untrusted" in methodology.contents[0].text
            providers = await client.read_resource("cite-nexus://providers")
            assert len(json.loads(providers.contents[0].text)) == 9
            prompts = await client.list_prompts()
            assert {p.name for p in prompts.prompts} == {"literature-review", "bibliography-audit"}
            prompt = await client.get_prompt(
                "literature-review", {"topic": "Reproducible research"}
            )
            assert "Reproducible research" in prompt.messages[0].content.text


@pytest.mark.parametrize("mode", ["2026-07-28", "legacy"])
async def test_real_stdio_process(mode, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "cite_nexus_mcp", "--env-file", str(env_file)]
    )
    async with Client(params, mode=mode, read_timeout_seconds=5) as client:
        result = await client.call_tool("list-providers", {})
        assert not result.is_error
        assert result.structured_content["providers"][0]["id"] == "crossref"
        normalized = await client.call_tool(
            "enhance-citation", {"bibtex": "@misc{key, title={A work}}"}
        )
        assert not normalized.is_error


@pytest.mark.parametrize("mode", ["2026-07-28", "legacy"])
async def test_real_streamable_http_process(mode, tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env_file = tmp_path / ".env"
    env_file.write_text("")
    with subprocess.Popen(  # noqa: ASYNC220 -- bounded local integration process
        [
            sys.executable,
            "-m",
            "cite_nexus_mcp",
            "--transport",
            "streamable-http",
            "--port",
            str(port),
            "--env-file",
            str(env_file),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:  # noqa: ASYNC220 -- local test process, bounded waits
        try:
            url = f"http://127.0.0.1:{port}/mcp"
            async with httpx.AsyncClient(timeout=1) as http:
                for _ in range(100):
                    if process.poll() is not None:
                        pytest.fail(process.stderr.read())
                    try:
                        await http.get(f"http://127.0.0.1:{port}/")
                        break
                    except httpx.TransportError:
                        await asyncio.sleep(0.05)
                else:
                    pytest.fail("HTTP server did not become ready")
            async with Client(url, mode=mode, read_timeout_seconds=5) as client:
                result = await client.call_tool("list-providers", {})
                assert not result.is_error
                assert len(result.structured_content["providers"]) == 9
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_cli_provider_listing_never_prints_secret(tmp_path):
    env = {**os.environ, "SERPAPI_API_KEY": "do-not-print-this-secret"}
    result = subprocess.run(
        [sys.executable, "-m", "cite_nexus_mcp", "--list-providers"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "do-not-print-this-secret" not in result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert next(p for p in data if p["id"] == "serpapi")["available"]
