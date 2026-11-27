import asyncio
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
from typing import Any, Literal, cast
from unittest.mock import ANY

import httpx2 as httpx
import jsonschema
import pytest
from mcp import Client, StdioServerParameters, types
from mcp.client.extension import ClientExtension, ResultClaim, advertise
from mcp.shared.exceptions import MCPError
from mcp.types import PromptReference, Result
from pydantic import TypeAdapter

from pancite.config import Settings
from pancite.http import HTTP
from pancite.providers import registry
from pancite.server import create_server
from pancite.service import ResearchService


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
            assert len(resources.resources) == 7
            methodology = await client.read_resource("pancite://methodology")
            assert "untrusted" in methodology.contents[0].text
            providers = await client.read_resource("pancite://providers")
            assert len(json.loads(providers.contents[0].text)) == 10
            prompts = await client.list_prompts()
            assert {p.name for p in prompts.prompts} == {"literature-review", "bibliography-audit"}
            prompt = await client.get_prompt(
                "literature-review", {"topic": "Reproducible research"}
            )
            assert "Reproducible research" in prompt.messages[0].content.text


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_tools_resources_and_prompts_describe_themselves(mode):
    async with Client(create_server(Settings()), mode=mode, read_timeout_seconds=5) as client:
        capabilities = client.server_capabilities
        assert not capabilities.tools.list_changed
        assert not capabilities.prompts.list_changed
        assert not capabilities.resources.list_changed
        assert not capabilities.resources.subscribe
        assert [i.mime_type for i in client.server_info.icons] == ["image/svg+xml", "image/png"]
        if mode == "auto":
            stamp = (await client.call_tool("list-providers", {})).meta[types.SERVER_INFO_META_KEY]
            assert stamp["name"] == "pancite" and "icons" not in stamp
        provider_ids = list(registry(cast(HTTP, None), Settings()))
        for tool in (await client.list_tools()).tools:
            assert tool.title and tool.annotations.title == tool.title, tool.name
            assert all(icon.src.startswith("data:image/") for icon in tool.icons)
            properties = tool.input_schema.get("properties", {})
            for name, schema in properties.items():
                assert schema.get("description"), f"{tool.name}.{name}"
            if "providers" in properties:
                array = properties["providers"]["anyOf"][0]
                assert array["items"]["enum"] == provider_ids
                assert (array["minItems"], array["maxItems"]) == (1, len(provider_ids))
            for one, other in [("identifier", "scholar_id"), ("citation", "identifier")]:
                if one in properties and other in properties:
                    for name in (one, other):
                        assert "exactly one of" in properties[name]["description"]
                    assert "oneOf" not in tool.input_schema
        graph = next(t for t in (await client.list_tools()).tools if t.name == "related-papers")
        assert graph.input_schema["properties"]["provider"]["enum"] == [
            "semantic_scholar",
            "europe_pmc",
            "openalex",
            "serpapi",
            "searchapi",
        ]
        for resource in (await client.list_resources()).resources:
            assert resource.title and resource.description, resource.uri
        for prompt in (await client.list_prompts()).prompts:
            assert prompt.title
            assert all(argument.description for argument in prompt.arguments)
        completed = await client.complete(
            PromptReference(type="ref/prompt", name="literature-review"),
            {"name": "scope", "value": "sc"},
        )
        assert completed.completion.values == ["scoping"]


@pytest.mark.parametrize("mode", ["2026-07-28", "legacy"])
async def test_real_stdio_process(mode, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "pancite", "--env-file", str(env_file)]
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
            "pancite",
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
                assert len(result.structured_content["providers"]) == 10
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_cli_provider_listing_never_prints_secret(tmp_path):
    env = {
        **os.environ,
        "SERPAPI_API_KEY": "do-not-print-this-secret",
        "SEARCHAPI_API_KEY": "do-not-print-searchapi-secret",
    }
    result = subprocess.run(
        [sys.executable, "-m", "pancite", "--list-providers"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "do-not-print-this-secret" not in result.stdout + result.stderr
    assert "do-not-print-searchapi-secret" not in result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert next(p for p in data if p["id"] == "serpapi")["available"]
    assert next(p for p in data if p["id"] == "searchapi")["available"]


def test_cli_reads_only_an_explicitly_named_env_file(tmp_path):
    (tmp_path / ".env").write_text("SERPAPI_API_KEY=from-the-launch-directory\n")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"SERPAPI_API_KEY", "SERP_API_KEY", "SERPAPI_KEY"}
    }

    def serpapi_available(*extra: str) -> bool:
        result = subprocess.run(
            [sys.executable, "-m", "pancite", *extra, "--list-providers"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return next(p for p in json.loads(result.stdout) if p["id"] == "serpapi")["available"]

    assert not serpapi_available()
    assert not serpapi_available("--no-env-file")
    assert serpapi_available("--env-file", str(tmp_path / ".env"))


def _frontmatter(text: str) -> dict[str, str]:
    head = text.split("---\n")[1]
    pairs = (line.split(": ", 1) for line in head.splitlines())
    return {key: json.loads(value) if value.startswith('"') else value for key, value in pairs}


async def _request(client: Client, method: str, params: dict[str, Any]) -> dict[str, Any]:
    request = types.Request[dict[str, Any], str](method=method, params=params)
    return await client.session.send_request(request, TypeAdapter(dict[str, Any]))


async def test_skills_manifests_match_the_files_resources_read_returns():
    async with Client(create_server(Settings()), mode="auto", read_timeout_seconds=5) as client:
        capabilities = client.server_capabilities
        assert capabilities.extensions["io.modelcontextprotocol/skills"] == {}
        assert capabilities.resources is not None
        listing = await _request(client, "skills/list", {})
        assert (listing["ttlMs"], listing["cacheScope"]) == (3600000, "public")
        names = []
        for skill in listing["skills"]:
            name = skill["frontmatter"]["name"]
            names.append(name)
            assert skill["uri"] == f"skill://pancite/{name}/SKILL.md"
            assert [r["uri"] for r in skill["resources"]] == [skill["uri"]]
            for entry in skill["resources"]:
                read = await client.read_resource(entry["uri"])
                data = read.contents[0].text.encode()
                assert entry["size"] == len(data)
                assert entry["digest"] == "sha256:" + hashlib.sha256(data).hexdigest()
                assert read.contents[0].mime_type == "text/markdown"
                assert _frontmatter(read.contents[0].text) == skill["frontmatter"]
            fetched = await _request(client, "skills/get", {"uri": skill["uri"]})
            assert fetched["skill"] == skill
        assert names == [
            "evidence-policy",
            "research-workflows",
            "literature-review",
            "bibliography-audit",
        ]
        with pytest.raises(MCPError) as unknown:
            await _request(client, "skills/get", {"uri": "skill://pancite/missing/SKILL.md"})
        assert unknown.value.error.code == -32602
    async with Client(create_server(Settings()), mode="legacy", read_timeout_seconds=5) as client:
        with pytest.raises(MCPError) as legacy:
            await _request(client, "skills/list", {})
        assert legacy.value.error.code == -32601
        uris = {str(r.uri) for r in (await client.list_resources()).resources}
        assert "skill://pancite/literature-review/SKILL.md" in uris


def _file(body: bytes, name: str, mime: str, **changes: Any) -> dict[str, Any]:
    digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
    file = {
        "id": "f1",
        "name": name,
        "mimeType": mime,
        "size": len(body),
        "data": base64.b64encode(body).decode(),
        "digest": {"algorithm": "sha-256", "value": digest},
    }
    return {**file, **changes}


async def test_file_arguments_are_listed_publicly_and_checked_before_use(records):
    requests: list[str] = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200, json={"message": records["crossref"]})

    files = [advertise("io.modelcontextprotocol/files")]
    entry = b"@article{k, title={Reliable Research & Data}, year={2024}, doi={10.1234/example}}\n"
    ris = b"TY  - JOUR\nTI  - Reliable Research & Data\nPY  - 2024\nDO  - 10.1234/example\nER  -\n"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            plain = {t.name: t for t in (await client.list_tools()).tools}
            inline = await client.call_tool(
                "enhance-citation", {"file": _file(entry, "refs.bib", "text/plain")}
            )
        async with Client(
            create_server(service=service), read_timeout_seconds=5, extensions=files
        ) as client:
            assert client.server_capabilities.extensions["io.modelcontextprotocol/files"] == {
                "maxInlineBytes": 1048576
            }
            tools = {t.name: t for t in (await client.list_tools()).tools}
            bib = await client.call_tool(
                "verify-citation", {"file": _file(entry, "refs.bib", "application/x-bibtex")}
            )
            from_ris = await client.call_tool(
                "verify-citation", {"file": _file(ris, "one.ris", "text/plain")}
            )
            before = len(requests)
            rejected = [
                await client.call_tool("verify-citation", {"file": file})
                for file in (
                    _file(entry, "refs.bib", "text/plain", size=3),
                    _file(
                        entry,
                        "refs.bib",
                        "text/plain",
                        digest={"algorithm": "sha-256", "value": "AA"},
                    ),
                    {
                        k: v
                        for k, v in _file(entry, "refs.bib", "text/plain").items()
                        if k != "data"
                    },
                    _file(entry, "refs.bib", "text/plain", data=None),
                    _file(entry, "refs.bib", "text/plain", data="not base64!"),
                    _file(entry, "paper.pdf", "application/pdf"),
                    _file(entry, "refs.bib", "text/plain", size=100_001),
                )
            ]
            both = await client.call_tool(
                "verify-citation",
                {"citation": "10.1234/example", "file": _file(entry, "refs.bib", "text/plain")},
            )
            secret = base64.b64encode(b"private-file-bytes").decode()
            missing_mime = await client.call_tool(
                "enhance-citation",
                {"file": {"id": "f1", "size": 18, "data": secret}},
            )
            unknown_with_file = await client.call_tool(
                "enhance-citation",
                {
                    "file": _file(b"private-file-bytes", "refs.bib", "text/plain"),
                    "unexpected": True,
                },
            )
    assert [t.model_dump() for t in plain.values()] == [t.model_dump() for t in tools.values()]
    for name in ("verify-citation", "enhance-citation"):
        schema = tools[name].input_schema["properties"]["file"]
        assert schema["type"] == "object" and "default" not in schema
        assert schema["required"] == ["id", "mimeType", "size"]
        assert schema["x-mcp-file"]["maxSize"] == 100_000
    accept = {
        name: set(tools[name].input_schema["properties"]["file"]["x-mcp-file"]["accept"])
        for name in tools
        if "file" in tools[name].input_schema["properties"]
    }
    assert set(accept) == {"verify-citation", "enhance-citation"}
    assert {".bib", ".ris", ".json", "text/plain"} <= accept["verify-citation"]
    assert {".bib", "text/plain"} <= accept["enhance-citation"]
    assert ".ris" not in accept["enhance-citation"]
    assert not inline.is_error, inline.content
    assert "title = {Reliable Research" in inline.structured_content["bibtex"]
    assert bib.structured_content["status"] == "verified", bib.content
    assert bib.structured_content["match"] == "metadata"
    assert from_ris.structured_content["match"] == "metadata", from_ris.content
    messages = [result.content[0].text for result in rejected]
    assert all(result.is_error for result in rejected), messages
    for message, expected in zip(
        messages,
        [
            "declares size 3",
            "sha-256 digest",
            "send the file inline",
            "null data",
            "not valid base64",
            "not an accepted type",
            "the limit is 100000",
        ],
        strict=True,
    ):
        assert expected in message
    assert len(requests) == before
    assert both.is_error
    assert missing_mime.is_error and secret not in missing_mime.content[0].text
    assert unknown_with_file.is_error and secret not in unknown_with_file.content[0].text


class _TaskCreated(Result):
    result_type: Literal["task"] = "task"
    task_id: str
    status: str
    ttl_ms: int
    poll_interval_ms: int


class _Tasks(ClientExtension):
    identifier = "io.modelcontextprotocol/tasks"

    def __init__(self) -> None:
        self.created: list[_TaskCreated] = []
        self.final: list[dict[str, Any]] = []

    def claims(self) -> list[ResultClaim[Any]]:
        return [ResultClaim(result_type="task", model=_TaskCreated, resolve=self._resolve)]

    async def _resolve(self, created: _TaskCreated, ctx: Any) -> types.CallToolResult:
        self.created.append(created)
        while True:
            request = types.Request[dict[str, Any], str](
                method="tasks/get", params={"taskId": created.task_id}
            )
            task = await ctx.session.send_request(request, TypeAdapter(dict[str, Any]))
            if task["status"] != "working":
                self.final.append(task)
                if task["status"] == "completed":
                    return types.CallToolResult.model_validate(task["result"])
                text = types.TextContent(type="text", text=task["status"])
                return types.CallToolResult(content=[text], is_error=True)
            await asyncio.sleep(0.02)


async def test_batches_run_as_tasks_for_declaring_clients_and_stop_on_cancel(records):
    delay = {"seconds": 0.0}
    inflight: list[str] = []
    started = asyncio.Event()

    async def handler(request):
        inflight.append(str(request.url))
        started.set()
        try:
            await asyncio.sleep(delay["seconds"])
        finally:
            inflight.remove(str(request.url))
        return httpx.Response(200, json={"message": records["crossref"]})

    batch = {"identifiers": ["10.1234/example"], "format": "bibtex"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        settings = Settings(operation_timeout=1, cache_ttl=0)
        service = ResearchService(settings, HTTP(settings, http_client))
        tasks = _Tasks()
        async with Client(
            create_server(service=service), read_timeout_seconds=5, extensions=[tasks]
        ) as client:
            assert client.server_capabilities.extensions["io.modelcontextprotocol/tasks"] == {}
            result = await client.call_tool("batch-citations", batch)
            created = tasks.created[0]
            assert (created.status, created.ttl_ms, created.poll_interval_ms) == (
                "working",
                3600000,
                1000,
            )
            assert tasks.final[0]["status"] == "completed"
            assert result.structured_content["items"][0]["citation"]["format"] == "bibtex"

            await client.call_tool("get-citation", {"identifier": "10.1234/example"})
            assert len(tasks.created) == 1

            bad_providers = await client.call_tool(
                "search-papers", {"query": "q", "providers": [{"bad": 1}]}
            )
            empty_providers = await client.call_tool(
                "search-papers", {"query": "q", "providers": []}
            )
            assert bad_providers.is_error and empty_providers.is_error
            assert len(tasks.created) == 1

            failed = await client.call_tool(
                "batch-citations", {"identifiers": ["10.1234/example"] * 21}
            )
            assert failed.is_error and tasks.final[-1]["status"] == "completed"

            delay["seconds"] = 1.2
            slow = await client.call_tool("batch-citations", batch)
            assert slow.structured_content["items"][0]["citation"], "a task run has no time budget"
            timed_out = await client.call_tool("resolve-paper", {"identifier": "10.1234/example"})
            assert timed_out.is_error and "time budget" in timed_out.content[0].text

            delay["seconds"] = 30
            started.clear()
            running = asyncio.create_task(client.call_tool("batch-citations", batch))
            await started.wait()
            task_id = tasks.created[-1].task_id
            assert await _request(client, "tasks/update", {"taskId": task_id, "other": 1}) == {
                "resultType": "complete",
                "_meta": ANY,
            }
            await _request(client, "tasks/cancel", {"taskId": task_id})
            cancelled = await asyncio.wait_for(running, 2)
            assert cancelled.is_error and tasks.final[-1]["status"] == "cancelled"
            assert not inflight
            for method in ("tasks/get", "tasks/update", "tasks/cancel"):
                with pytest.raises(MCPError) as unknown:
                    await _request(client, method, {"taskId": "unknown"})
                assert unknown.value.error.code == -32602

        delay["seconds"] = 0
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            assert not (await client.call_tool("batch-citations", batch)).is_error
            with pytest.raises(MCPError) as undeclared:
                await _request(client, "tasks/get", {"taskId": task_id})
            assert undeclared.value.error.code == -32021
        legacy = _Tasks()
        async with Client(
            create_server(service=service),
            mode="legacy",
            read_timeout_seconds=5,
            extensions=[legacy],
        ) as client:
            assert not (await client.call_tool("batch-citations", batch)).is_error
            assert not legacy.created
            with pytest.raises(MCPError) as missing:
                await _request(client, "tasks/get", {"taskId": task_id})
            assert missing.value.error.code == -32601


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
                (
                    "search-papers",
                    {"query": "q", "providers": ["typo"]},
                    "Input should be 'crossref'",
                ),
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


async def test_search_records_are_compact_by_default_and_full_on_request(records):
    def handler(_):
        return httpx.Response(200, json={"message": {"items": [records["crossref"]]}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            tools = (await client.list_tools()).tools
            search = next(t for t in tools if t.name == "search-papers")
            assert search.input_schema["properties"]["detail"]["enum"] == [
                "minimal",
                "compact",
                "full",
            ]
            assert search.input_schema["properties"]["detail"]["default"] == "compact"
            compact = await client.call_tool(
                "search-papers", {"query": "q", "providers": ["crossref"]}
            )
            full = await client.call_tool(
                "search-papers", {"query": "q", "providers": ["crossref"], "detail": "full"}
            )
    assert not compact.is_error and not full.is_error
    compact_paper = compact.structured_content["papers"][0]
    assert compact_paper["field_sources"] == {}
    assert compact_paper["sources"][0]["provider"] == "crossref"
    assert full.structured_content["papers"][0]["field_sources"]["title"] == ["crossref"]
    jsonschema.validate(compact.structured_content, search.output_schema)


async def test_text_content_is_the_structured_result_without_indentation(records):
    def handler(_):
        return httpx.Response(200, json={"message": records["crossref"]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            result = await client.call_tool("resolve-paper", {"identifier": "10.1234/example"})
    assert not result.is_error
    text = result.content[0].text
    assert "\n" not in text
    assert json.loads(text) == result.structured_content


async def test_minimal_search_caps_total_and_drops_defaults(records):
    def handler(request):
        if request.url.host == "api.crossref.org":
            items = [dict(records["crossref"], DOI=f"10.1234/x{i}") for i in range(5)]
            return httpx.Response(200, json={"message": {"items": items}})
        if request.url.host == "api.datacite.org":
            return httpx.Response(200, json={"data": [records["datacite"]] * 5, "meta": {}})
        return httpx.Response(200, json={"resultList": {"result": []}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            tools = (await client.list_tools()).tools
            search = next(t for t in tools if t.name == "search-papers")
            assert "PER PROVIDER" in search.description and "Example:" in search.description
            args = {"query": "q", "limit": 5}
            compact = await client.call_tool("search-papers", args)
            minimal = await client.call_tool(
                "search-papers", {**args, "limit_total": 3, "detail": "minimal"}
            )
    assert not minimal.is_error, minimal.content
    data = minimal.structured_content
    assert data["returned"] == len(data["papers"]) == 3
    assert any("limit_total" in w for w in data["warnings"])
    paper = data["papers"][0]
    assert set(paper) <= {"id", "title", "identifiers", "authors", "year", "venue", "warnings"}
    assert set(paper["identifiers"]) <= {"doi", "arxiv", "pmid"}
    assert json.loads(minimal.content[0].text) == data
    assert len(minimal.content[0].text) * 4 < len(compact.content[0].text)
    jsonschema.validate(data, search.output_schema)


async def test_verify_accepts_identifier_alias_and_reports_match_kind(records):
    bare = {k: v for k, v in records["crossref"].items() if k != "abstract"}

    def handler(request):
        if "noabs" in str(request.url):
            return httpx.Response(200, json={"message": dict(bare, DOI="10.1234/noabs")})
        return httpx.Response(200, json={"message": records["crossref"]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        service = ResearchService(Settings(), HTTP(Settings(), http_client))
        async with Client(create_server(service=service), read_timeout_seconds=5) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert all("Example:" in t.description for t in tools.values())
            assert "NEVER checks whether the paper supports" in tools["verify-citation"].description
            alias = await client.call_tool("verify-citation", {"identifier": "10.1234/example"})
            both = await client.call_tool(
                "verify-citation", {"identifier": "10.1234/example", "citation": "10.1234/example"}
            )
            matched = await client.call_tool(
                "verify-citation",
                {"citation": "10.1234/example", "expected_title": "Reliable Research & Data"},
            )
            resolved = await client.call_tool("resolve-paper", {"identifier": "10.1234/noabs"})
    assert not alias.is_error, alias.content
    assert alias.structured_content["status"] == "verified"
    assert alias.structured_content["match"] == "identifier"
    assert alias.structured_content["claim_support"] == "not_checked"
    assert both.is_error
    assert matched.structured_content["match"] == "metadata"
    paper = resolved.structured_content["paper"]
    assert paper["abstract"] is None
    assert "Do not infer findings" in paper["abstract_missing_reason"]
    jsonschema.validate(alias.structured_content, tools["verify-citation"].output_schema)
