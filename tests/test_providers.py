import httpx2 as httpx
import pytest
from pydantic import SecretStr

from cite_nexus_mcp.config import Settings
from cite_nexus_mcp.http import HTTP
from cite_nexus_mcp.identifiers import Identifier
from cite_nexus_mcp.providers import registry


def settings():
    return Settings(
        retries=0,
        openalex_api_key=SecretStr("openalex-test"),
        serpapi_api_key=SecretStr("serp-test"),
        scopus_api_key=SecretStr("scopus-test"),
        wos_api_key=SecretStr("wos-test"),
    )


@pytest.mark.parametrize(
    "name",
    [
        "crossref",
        "datacite",
        "europe_pmc",
        "semantic_scholar",
        "openalex",
        "serpapi",
        "scopus",
        "wos",
    ],
)
def test_native_metadata_is_normalized(name, records):
    provider = registry(None, settings())[name]
    paper = provider.parse(records[name])
    assert paper.title == "Reliable Research & Data"
    assert paper.year == 2024
    assert paper.sources[0].provider == name
    assert paper.sources[0].retrieved_at
    assert paper.field_sources["title"] == [name]
    if name != "serpapi":
        assert paper.identifiers["doi"] == "10.1234/example"
    else:
        assert paper.abstract is None
        assert not paper.authors_complete
        assert paper.identifiers["scholar"] == "123456789"
        assert paper.metrics[0].count == 2300
    if name == "scopus":
        assert not paper.authors_complete
        assert paper.metrics[0].count == 1200


def test_arxiv_is_a_preprint(arxiv_xml):
    paper = registry(None, settings())["arxiv"].parse_feed(arxiv_xml)[0]
    assert paper.identifiers["arxiv"] == "2403.12345"
    assert paper.type == "preprint"
    assert paper.access[0].is_open
    assert paper.authors[0].name == "Ada Lovelace"


def test_xml_external_entities_are_rejected():
    from defusedxml.common import DefusedXmlException

    with pytest.raises(DefusedXmlException):
        registry(None, settings())["arxiv"].parse_feed(
            b'<!DOCTYPE feed [<!ENTITY x SYSTEM "file:///etc/passwd">]><feed>&x;</feed>'
        )


@pytest.mark.parametrize(
    "name",
    [
        "crossref",
        "datacite",
        "europe_pmc",
        "arxiv",
        "semantic_scholar",
        "openalex",
        "serpapi",
        "scopus",
        "wos",
    ],
)
async def test_search_request_contracts(name, records, arxiv_xml):
    requests = []
    responses = {
        "crossref": {"message": {"items": [records["crossref"]], "total-results": 21}},
        "datacite": {"data": [records["datacite"]], "meta": {"total": 21}},
        "europe_pmc": {"resultList": {"result": [records["europe_pmc"]]}, "hitCount": 21},
        "semantic_scholar": {"data": [records["semantic_scholar"]], "next": 20},
        "openalex": {"results": [records["openalex"]], "meta": {"count": 21}},
        "serpapi": {
            "organic_results": [records["serpapi"]],
            "serpapi_pagination": {"next": "https://serpapi.com/next"},
        },
        "scopus": {
            "search-results": {"entry": [records["scopus"]], "opensearch:totalResults": "21"}
        },
        "wos": {"hits": [records["wos"]], "metadata": {"total": 21}},
    }

    def handler(request):
        requests.append(request)
        return (
            httpx.Response(200, content=arxiv_xml)
            if name == "arxiv"
            else httpx.Response(200, json=responses[name])
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = registry(HTTP(settings(), client), settings())[name]
        page = await provider.search("research", 10, 0 if name == "europe_pmc" else 10)
    assert page.papers[0].title == "Reliable Research & Data"
    request = requests[0]
    assert request.url.scheme == "https"
    if name in {"datacite", "openalex", "wos"}:
        assert request.url.params.get("page[number]", request.url.params.get("page")) == "2"
    if name == "europe_pmc":
        assert request.url.params["cursorMark"] == "*"
    if name == "serpapi":
        assert request.url.params["api_key"] == "serp-test"
        assert request.url.params["engine"] == "google_scholar"
    if name == "scopus":
        assert request.headers["X-ELS-APIKey"] == "scopus-test"
        assert request.url.params["query"] == 'TITLE-ABS-KEY("research")'
    if name == "wos":
        assert request.headers["X-ApiKey"] == "wos-test"
        assert request.url.params["q"] == 'TS=("research")'


@pytest.mark.parametrize(
    ("name", "kind", "value"),
    [
        ("crossref", "doi", "10.1234/example"),
        ("datacite", "doi", "10.1234/example"),
        ("europe_pmc", "pmid", "12345678"),
        ("arxiv", "arxiv", "2403.12345"),
        ("semantic_scholar", "doi", "10.1234/example"),
        ("openalex", "openalex", "W12345678"),
        ("serpapi", "scholar", "123456789"),
        ("scopus", "scopus", "987654321"),
        ("wos", "wos", "000123456789"),
    ],
)
async def test_identifier_lookup_contracts(name, kind, value, records, arxiv_xml):
    payloads = {
        "crossref": {"message": records["crossref"]},
        "datacite": {"data": records["datacite"]},
        "europe_pmc": {"resultList": {"result": [records["europe_pmc"]]}},
        "semantic_scholar": records["semantic_scholar"],
        "openalex": records["openalex"],
        "serpapi": {"organic_results": [records["serpapi"]]},
        "scopus": {"search-results": {"entry": [records["scopus"]]}},
        "wos": records["wos"],
    }

    def handler(request):
        return (
            httpx.Response(200, content=arxiv_xml)
            if name == "arxiv"
            else httpx.Response(200, json=payloads[name])
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = registry(HTTP(settings(), client), settings())[name]
        paper = await provider.resolve(Identifier(kind, value))
    assert paper.identifiers[kind] == value


@pytest.mark.parametrize("direction", ["citations", "references"])
async def test_semantic_graph_preserves_direction(direction, records):
    seen = []
    key = "citingPaper" if direction == "citations" else "citedPaper"

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [{key: records["semantic_scholar"]}], "next": 10})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = registry(HTTP(settings(), client), settings())["semantic_scholar"]
        result = await provider.graph(Identifier("doi", "10.1234/example"), direction, 10, 0)
    assert seen[0].url.path.endswith("/" + direction)
    assert result.next_offset == 10
    assert result.papers[0].metrics[0].count == 910
