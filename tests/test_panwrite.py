import json
import os
import subprocess
import sys
import time

import httpx2 as httpx
import pytest
from mcp.server import MCPServer
from pydantic import ValidationError

from pancite.config import Settings
from pancite.http import HTTP
from pancite.panwrite import Request, execute, server_parameters
from pancite.server import create_server
from pancite.service import ResearchService


async def test_bridge_preserves_candidate_evidence_and_never_ranks_counts(records):
    record = records["crossref"]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": {"items": [record]}})
        )
    ) as client:
        settings = Settings()
        server = create_server(service=ResearchService(settings, HTTP(settings, client)))
        data = await execute(Request(query="reliable", providers=["crossref"], limit=1), server)
    assert data["schema_version"] == "pancite.panwrite/v1"
    paper = data["results"][0]
    assert paper["verification"] == "candidate"
    assert "citationCount" not in paper
    assert "wtfp_status" not in paper["bibtex"]
    assert paper["pancite"]["sources"][0]["provider"] == "crossref"
    assert paper["pancite"]["field_sources"]["title"] == ["crossref"]
    assert data["metadata"]["errors"] == []


async def test_bridge_passes_detail_and_limit_total_and_echoes_them(records):
    items = [dict(records["crossref"], DOI=f"10.1234/x{i}") for i in range(5)]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": {"items": items}})
        )
    ) as client:
        settings = Settings()
        server = create_server(service=ResearchService(settings, HTTP(settings, client)))
        full = await execute(Request(query="q", providers=["crossref"], limit=5), server)
        minimal = await execute(
            Request(query="q", providers=["crossref"], limit=5, limit_total=2, detail="minimal"),
            server,
        )
    assert full["metadata"]["detail"] == "full" and full["metadata"]["limit_total"] is None
    assert full["results"][0]["pancite"]["abstract"] == full["results"][0]["abstract"]
    assert minimal["metadata"]["detail"] == "minimal"
    assert minimal["metadata"]["limit_total"] == 2
    assert minimal["metadata"]["total"] == len(minimal["results"]) == 2
    record = minimal["results"][0]["pancite"]
    assert "abstract" not in record and "sources" not in record
    assert len(json.dumps(minimal)) * 2 < len(json.dumps(full))


async def test_bridge_retains_partial_outages(records):
    def handler(request):
        if "crossref" in request.url.host:
            return httpx.Response(200, json={"message": {"items": [records["crossref"]]}})
        return httpx.Response(503)

    settings = Settings(retries=0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        server = create_server(service=ResearchService(settings, HTTP(settings, client)))
        data = await execute(Request(query="reliable", providers=["crossref", "datacite"]), server)
    assert data["results"]
    assert data["metadata"]["errors"][0]["provider"] == "datacite"


async def test_bridge_rejects_incompatible_mcp():
    server = MCPServer("incompatible")

    @server.tool(name="search-papers")
    def search_papers(query: str, providers: list[str], limit: int, include_abstract: bool) -> dict:
        return {"invented": "not a scholarly search response"}

    with pytest.raises(ValueError):
        await execute(Request(query="x"), server)


@pytest.mark.parametrize(
    "changes",
    [
        {"limit": 26},
        {"limit": True},
        {"timeout_seconds": "10"},
        {"query": "x" * 513},
        {"providers": []},
        {"providers": ["unknown"]},
        {"command": "anything"},
        {"api_key": "sensitive"},
        {"schema_version": "different/v2"},
        {"detail": "verbose"},
        {"limit_total": 0},
        {"limit_total": "5"},
    ],
)
def test_bridge_input_bounds(changes):
    with pytest.raises(ValidationError):
        Request.model_validate({"query": "topic", **changes})


def test_bridge_environment_and_real_stdio_check(tmp_path, monkeypatch):
    monkeypatch.setenv("UNRELATED_TOKEN", "do-not-forward")
    monkeypatch.setenv("PANCITE_DEFAULT_PROVIDERS", "serpapi")
    monkeypatch.setenv("PYTHONPATH", "/untrusted/module/path")
    assert "UNRELATED_TOKEN" not in server_parameters().env
    assert "PANCITE_DEFAULT_PROVIDERS" not in server_parameters().env
    assert "PYTHONPATH" not in server_parameters().env
    (tmp_path / ".env").write_text(
        "SERPAPI_API_KEY=do-not-load\nPANCITE_DEFAULT_PROVIDERS=serpapi\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"SERPAPI_API_KEY", "SERPAPI_KEY", "SERP_API_KEY", "PYTHONPATH"}
    }
    result = subprocess.run(
        [sys.executable, "-m", "pancite.panwrite", "--check"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert "do-not-load" not in result.stdout + result.stderr
    providers = json.loads(result.stdout)["providers"]["providers"]
    assert next(p for p in providers if p["id"] == "crossref")["default"]
    assert not next(p for p in providers if p["id"] == "serpapi")["available"]


def test_bridge_invalid_request_never_echoes_private_input():
    result = subprocess.run(
        [sys.executable, "-m", "pancite.panwrite"],
        input=json.dumps({"query": "private-query", "token": "private-secret"}),
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1
    assert not result.stdout
    assert "private" not in result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process-group and signal qualification")
@pytest.mark.parametrize("cancel", [False, True], ids=["deadline", "sigterm"])
def test_bridge_closes_hung_stdio_server(tmp_path, cancel):
    ready = tmp_path / "provider.pid"
    server = tmp_path / "hung_server.py"
    server.write_text(
        "import os,time\nfrom mcp.server import MCPServer\n"
        "app=MCPServer('hanging-fixture')\n"
        "@app.tool(name='search-papers')\n"
        "async def search_papers(query:str,providers:list[str],limit:int,include_abstract:bool)->dict:\n"
        f"    open({str(ready)!r},'w').write(str(os.getpid()))\n"
        "    time.sleep(60)\n    return {}\n"
        "app.run()\n"
    )
    bridge = tmp_path / "bridge.py"
    bridge.write_text(
        "from pancite import panwrite\nfrom mcp import StdioServerParameters\n"
        f"panwrite.server_parameters=lambda: StdioServerParameters(command={sys.executable!r},args=[{str(server)!r}])\n"
        "panwrite.run()\n"
    )
    with subprocess.Popen(
        [sys.executable, str(bridge)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        process.stdin.write(json.dumps({"query": "topic", "timeout_seconds": 30 if cancel else 3}))
        process.stdin.close()
        process.stdin = None
        pid = None
        try:
            for _ in range(150):
                if ready.exists():
                    pid = int(ready.read_text())
                    break
                if process.poll() is not None:
                    pytest.fail("Bridge exited before the hanging provider started")
                time.sleep(0.02)
            assert pid is not None, "MCP provider was not reached"
            if cancel:
                process.terminate()
            stdout, stderr = process.communicate(timeout=12)
            assert process.returncode == 124, stderr
            assert not stdout
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            if pid is not None:
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
