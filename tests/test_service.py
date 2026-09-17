import asyncio

import httpx2 as httpx
import pytest

from cite_nexus_mcp.config import Settings
from cite_nexus_mcp.http import HTTP
from cite_nexus_mcp.models import Author, Paper, ProviderIssue
from cite_nexus_mcp.service import ResearchService, deduplicate, merge, same_work


def work(doi="10.1234/a", title="An exact title of a research paper", **kwargs):
    return Paper(
        id="doi:" + doi,
        identifiers={"doi": doi},
        title=title,
        authors=[Author(name="Ada Lovelace", family="Lovelace")],
        year=2024,
        **kwargs,
    )


def test_deduplication_does_not_merge_conflicting_dois():
    a, b = work(), work("10.1234/b")
    b.identifiers["pmid"] = "123"
    a.identifiers["pmid"] = "123"
    assert not same_work(a, b)
    assert len(deduplicate([a, b])) == 2


def test_sparse_duplicate_enriches_without_losing_evidence():
    a, b = work(), work(abstract="Evidence.", venue="Journal")
    b.field_sources["abstract"] = ["datacite"]
    result = deduplicate([a, b])
    assert len(result) == 1
    assert result[0].abstract == "Evidence."
    assert result[0].field_sources["abstract"] == ["datacite"]


def test_metadata_disagreement_stays_visible():
    a, b = work(), work()
    b.year = 2025
    result = merge(a, b)
    assert result.year == 2024
    assert any("disagree on year" in w for w in result.warnings)


async def test_search_partial_failure_and_duplicate_merge(records):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.host == "api.crossref.org":
            return httpx.Response(
                200, json={"message": {"items": [records["crossref"]], "total-results": 1}}
            )
        if request.url.host == "api.datacite.org":
            return httpx.Response(200, json={"data": [records["datacite"]], "meta": {"total": 1}})
        return httpx.Response(429, headers={"Retry-After": "60"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(retries=0), HTTP(Settings(retries=0), client))
        result = await service.search("research")
    assert len(calls) == 3
    assert result.returned == 1
    assert {s.provider for s in result.papers[0].sources} == {"crossref", "datacite"}
    assert result.issues[0].code == "rate_limited"
    assert result.papers[0].metrics[0].count == 1250


async def test_provider_failure_is_not_successful_empty_search():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(503))
    ) as client:
        settings = Settings(retries=0)
        service = ResearchService(settings, HTTP(settings, client))
        with pytest.raises(ValueError, match="All selected providers failed"):
            await service.search("query")
        with pytest.raises(ValueError, match="Unknown provider"):
            await service.search("query", ["typo"])


async def test_exact_lookup_rejects_wrong_doi_and_falls_back(records):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        if request.url.host == "api.crossref.org":
            wrong = {**records["crossref"], "DOI": "10.1234/wrong"}
            return httpx.Response(200, json={"message": wrong})
        return httpx.Response(200, json={"data": records["datacite"]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        result = await service.resolve("10.1234/example")
    assert result.paper.identifiers["doi"] == "10.1234/example"
    assert result.issues[0].code == "identifier_mismatch"
    assert calls == ["api.crossref.org", "api.datacite.org"]


async def test_paid_provider_requires_configuration_before_network():
    def handler(_):
        raise AssertionError("No request should be sent")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        with pytest.raises(ValueError, match="not_configured"):
            await service.search("query", ["serpapi"])


async def test_verification_compares_supplied_fields_and_distinguishes_outage(records):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"message": records["crossref"]})
        )
    ) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        mismatch = await service.verify(
            "10.1234/example", expected_title="A different title", expected_year=2023
        )
        assert mismatch.status == "mismatch" and len(mismatch.differences) == 2
        verified = await service.verify(
            "10.1234/example", expected_title="Reliable Research & Data", expected_year=2024
        )
        assert verified.status == "verified"
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(503))
    ) as client:
        settings = Settings(retries=0)
        service = ResearchService(settings, HTTP(settings, client))
        result = await service.verify("10.1234/example")
        assert result.status == "unavailable"


async def test_title_only_match_remains_ambiguous(records):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"message": {"items": [records["crossref"]], "total-results": 1}}
            )
        )
    ) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        result = await service.verify("Reliable Research & Data", providers=["crossref"])
    assert result.status == "ambiguous"


async def test_batch_preserves_order_progress_and_partial_failure(records):
    def handler(request):
        if "missing" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(200, json={"message": records["crossref"]})

    progress = []

    async def report(done, total):
        progress.append((done, total))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        result = await service.batch(
            ["10.1234/example", "10.1234/missing", "bad id"],
            providers=["crossref"],
            progress=report,
        )
    assert result.completed == 1 and result.failed == 2
    assert [i.identifier for i in result.items] == ["10.1234/example", "10.1234/missing", "bad id"]
    assert progress == [(1, 3), (2, 3), (3, 3)]


async def test_cancellation_propagates_from_provider():
    async with httpx.AsyncClient() as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))

        async def cancelled():
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await service.attempt(service.providers["crossref"], cancelled)


async def test_provider_time_budget():
    settings = Settings(operation_timeout=1)
    async with httpx.AsyncClient() as client:
        service = ResearchService(settings, HTTP(settings, client))

        async def stalled():
            await asyncio.sleep(2)

        outcome = await service.attempt(service.providers["crossref"], stalled)
    assert isinstance(outcome, ProviderIssue) and outcome.code == "timeout"


def test_preprint_and_published_version_remain_separate():
    preprint = work(type="preprint")
    preprint.identifiers["arxiv"] = "2403.12345"
    published = work(type="journal-article")
    assert len(deduplicate([preprint, published])) == 2


async def test_native_cursor_paging_and_compact_results(records):
    tokens = []

    def handler(request):
        token = request.url.params["cursorMark"]
        tokens.append(token)
        record = {
            **records["europe_pmc"],
            "id": "111" if token == "*" else "222",
            "pmid": "111" if token == "*" else "222",
        }
        return httpx.Response(
            200,
            json={
                "resultList": {"result": [record]},
                "hitCount": 100,
                "nextCursorMark": "next-page" if token == "*" else "last-page",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        first = await service.search("query", ["europe_pmc"], limit=1)
        second = await service.search(
            "query",
            ["europe_pmc"],
            limit=1,
            cursor=first.next_cursors["europe_pmc"],
            include_abstract=True,
        )
        assert not first.next_offsets
        assert first.papers[0].abstract is None
        assert second.papers[0].abstract == "Measured evidence."
        assert first.papers[0].identifiers["pmid"] != second.papers[0].identifiers["pmid"]
        with pytest.raises(ValueError, match="cursor requires"):
            await service.search("query", ["crossref"], cursor="next-page")
    assert tokens == ["*", "next-page"]


async def test_unpaywall_enrichment_and_doi_validation(records):
    def handler(request):
        if request.url.host == "api.crossref.org":
            return httpx.Response(200, json={"message": records["crossref"]})
        assert request.url.params["email"] == "researcher@example.org"
        return httpx.Response(
            200,
            json={
                "doi": "10.1234/example",
                "oa_locations": [
                    {
                        "url_for_pdf": "https://repository.example.org/paper.pdf",
                        "license": "cc-by",
                        "version": "acceptedVersion",
                    }
                ],
            },
        )

    settings = Settings(unpaywall_email="researcher@example.org")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(settings, HTTP(settings, client))
        result = await service.open_access("10.1234/example")
    assert result.locations[0].provider == "unpaywall"
    assert result.locations[0].license == "cc-by"


async def test_graph_reports_provider_count_not_page_length(records):
    def handler(_):
        return httpx.Response(
            200, json={"data": [{"citingPaper": records["semantic_scholar"]}], "next": 10}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        result = await service.graph("10.1234/example", "citations")
        assert result.returned == 1
        assert result.papers[0].metrics[0].count == 910
        assert result.next_offset == 10


async def test_generated_bibtex_can_be_verified_without_escape_mismatches(records):
    from cite_nexus_mcp.citations import format_citation

    record = {
        **records["crossref"],
        "DOI": "10.1234/data_sets",
        "title": ["GPU & AI: 50% of data_sets #1 $2"],
    }

    def handler(request):
        assert request.url.path.endswith("/10.1234/data_sets")
        return httpx.Response(200, json={"message": record})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ResearchService(Settings(), HTTP(Settings(), client))
        paper = service.providers["crossref"].parse(record)
        result = await service.verify(format_citation(paper).citation)
    assert result.status == "verified"
