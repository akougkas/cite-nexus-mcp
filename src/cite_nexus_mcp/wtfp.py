"""Bounded WTF-P companion process using the official MCP client and stdio server.

The bridge accepts a single JSON request. No command, URL, credential or file path
can be supplied in that request. Search records remain unverified candidates.
"""

import argparse
import asyncio
import json
import os
import signal
import sys
import time
import uuid
from typing import Annotated, Any, Literal, Self

import anyio
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import Field, ValidationError, model_validator

from . import __version__
from .citations import bibtex, warnings
from .models import Model, ProvidersResult, SearchResult

SCHEMA: Literal["cite-nexus.wtfp/v1"] = "cite-nexus.wtfp/v1"
MAX_INPUT = 16384
MAX_OUTPUT = 2 * 1024 * 1024
Provider = Literal[
    "crossref",
    "datacite",
    "europe_pmc",
    "arxiv",
    "semantic_scholar",
    "openalex",
    "serpapi",
    "scopus",
    "wos",
]
# Forward runtime essentials and declared provider settings only. Do not inherit
# unrelated host tokens, Python injection options, proxies, or default providers.
ENVIRONMENT = (
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TEMP",
    "TMP",
    "CITE_NEXUS_CONTACT_EMAIL",
    "SEMANTIC_SCHOLAR_API_KEY",
    "OPENALEX_API_KEY",
    "SERPAPI_API_KEY",
    "SCOPUS_API_KEY",
    "SCOPUS_INSTTOKEN",
    "WOS_API_KEY",
)


class Request(Model):
    schema_version: Literal["cite-nexus.wtfp/v1"] = SCHEMA
    operation: Literal["search", "providers"] = "search"
    query: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    providers: Annotated[list[Provider], Field(min_length=1, max_length=9)] = [
        "crossref",
        "datacite",
        "europe_pmc",
    ]
    limit: Annotated[int, Field(strict=True, ge=1, le=25)] = 10
    year: Annotated[int, Field(strict=True, ge=1000, le=2200)] | None = None
    timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=600)] = 20

    @model_validator(mode="after")
    def require_search_query(self) -> Self:
        if self.operation == "search" and (not self.query or not self.query.strip()):
            raise ValueError("A search query is required")
        return self


def server_parameters() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "cite_nexus_mcp", "--no-env-file"],
        env={key: os.environ[key] for key in ENVIRONMENT if key in os.environ},
    )


async def execute(request: Request, server: Any = None) -> dict[str, Any]:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    # Use AnyIO cancellation so the SDK's shielded process-group shutdown can
    # finish. Native asyncio Task.cancel() can interrupt that cleanup.
    with anyio.fail_after(request.timeout_seconds):
        # Suppress SDK/server diagnostics here: a tool boundary must not relay
        # third-party exception bodies, private queries or environment values.
        with open(os.devnull, "w") as diagnostics:  # noqa: ASYNC230 -- local null device
            async with Client(
                server
                if server is not None
                else stdio_client(server_parameters(), errlog=diagnostics),
                read_timeout_seconds=request.timeout_seconds,
            ) as client:
                arguments: dict[str, Any] = {}
                tool = "list-providers"
                if request.operation == "search":
                    if not request.query or not request.query.strip():
                        raise ValueError("empty query")
                    tool = "search-papers"
                    arguments = {
                        "query": request.query,
                        "providers": list(dict.fromkeys(request.providers)),
                        "limit": min(request.limit, 20)
                        if "serpapi" in request.providers
                        else request.limit,
                        "include_abstract": True,
                    }
                    if request.year is not None:
                        arguments.update(year_from=request.year, year_to=request.year)
                result = await client.call_tool(tool, arguments)
    if result.is_error or result.structured_content is None:
        raise ValueError("MCP tool did not return a successful structured result")
    data = result.structured_content
    metadata: dict[str, Any] = {
        "backend": "cite-nexus",
        "version": __version__,
        "transport": "mcp-stdio",
        "request_id": request_id,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }
    if request.operation == "providers":
        return {
            "schema_version": SCHEMA,
            "providers": ProvidersResult.model_validate(data).model_dump(),
            "metadata": metadata,
        }
    search = SearchResult.model_validate(data)
    papers = search.papers[: request.limit]
    metadata.update(
        query=search.query,
        total=search.returned,
        returned=len(papers),
        providers=search.providers,
        errors=[issue.model_dump() for issue in search.issues],
        warnings=search.warnings,
        ordering="Provider ranks interleaved; no global relevance or citation-count ranking.",
        truncated=len(search.papers) > len(papers),
        # Keep provider page state explicitly separate from the displayed total limit.
        provider_limit=arguments["limit"],
        next_offsets=search.next_offsets,
        next_cursors=search.next_cursors,
    )
    return {
        "schema_version": SCHEMA,
        "results": [
            {
                "id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "doi": paper.identifiers.get("doi"),
                "venue": paper.venue,
                "authors": [author.model_dump(exclude_none=True) for author in paper.authors],
                "abstract": paper.abstract,
                "source": "cite-nexus",
                "url": paper.url,
                "externalIds": {"DOI": paper.identifiers["doi"]}
                if "doi" in paper.identifiers
                else {},
                "verification": "candidate",
                "bibtex": bibtex(paper),
                "warnings": warnings(paper),
                "citeNexus": paper.model_dump(),
            }
            for paper in papers
        ],
        "metadata": metadata,
    }


async def _supervised(request: Request) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    with anyio.CancelScope() as scope:
        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, scope.cancel)
        result = await execute(request)
    if scope.cancel_called:
        raise TimeoutError("Companion cancelled")
    return result


def run() -> None:
    parser = argparse.ArgumentParser(
        description="CiteNexus companion bridge for WTF-P (one JSON request on stdin)"
    )
    parser.add_argument("--version", action="version", version=f"cite-nexus-wtfp {__version__}")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check real MCP startup and provider configuration without API calls",
    )
    args = parser.parse_args()
    try:
        if args.check:
            request = Request(operation="providers")
        else:
            raw = sys.stdin.buffer.read(MAX_INPUT + 1)
            if len(raw) > MAX_INPUT:
                raise ValueError("request too large")
            payload = json.loads(raw)
            request = Request.model_validate(payload)
            if request.operation == "search" and "query" not in payload:
                raise ValueError("query is required")
        output = json.dumps(asyncio.run(_supervised(request)), ensure_ascii=False).encode("utf-8")
        if len(output) > MAX_OUTPUT:
            raise ValueError("response too large")
        sys.stdout.buffer.write(output + b"\n")
    except (ValidationError, ValueError, UnicodeError):
        print(
            json.dumps(
                {
                    "error": "Invalid request or incompatible CiteNexus response; check bridge versions and input bounds."
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except (TimeoutError, asyncio.CancelledError, KeyboardInterrupt):
        print(json.dumps({"error": "CiteNexus request timed out."}), file=sys.stderr)
        raise SystemExit(124) from None
    except Exception:
        print(
            json.dumps({"error": "CiteNexus MCP connection failed; run cite-nexus-wtfp --check."}),
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    run()
