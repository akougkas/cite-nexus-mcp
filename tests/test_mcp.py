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


async def test_unknown_identifier_and_invalid_input_are_readable_tool_errors():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))
    ) as http_client:
        settings = Settings(retries=0)
        service = ResearchService(settings, HTTP(settings, http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            for name, arguments in [
                ("get-citation", {"identifier": "10.1109/HPDC.2019.00023", "format": "bibtex"}),
                ("resolve-paper", {"identifier": "10.1109/HPDC.2019.00023"}),
            ]:
                failed = await client.call_tool(name, arguments)
                assert failed.is_error, name
                text = failed.content[0].text
                assert "not_found" in text, text
                assert "crossref, datacite, europe_pmc" in text, text
                assert "search-papers" in text, text
            for name, arguments, expected in [
                ("resolve-paper", {"identifier": "not an id"}, "Use a DOI"),
                ("search-papers", {"query": "q", "providers": ["typo"]}, "Unknown provider"),
                ("enhance-citation", {"bibtex": "invalid"}, "BibTeX"),
            ]:
                failed = await client.call_tool(name, arguments)
                assert failed.is_error, name
                assert expected in failed.content[0].text, failed.content[0].text


async def test_unknown_arguments_are_rejected_before_any_request():
    def handler(_):
        raise AssertionError("No request should be sent")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            tools = (await client.list_tools()).tools
            for tool in tools:
                assert tool.input_schema.get("additionalProperties") is False, tool.name
            search = next(t for t in tools if t.name == "search-papers")
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate({"query": "q", "max_results": 3}, search.input_schema)
            failed = await client.call_tool("search-papers", {"query": "q", "max_results": 3})
            assert failed.is_error
            text = failed.content[0].text
            assert "max_results" in text and "limit" in text, text
