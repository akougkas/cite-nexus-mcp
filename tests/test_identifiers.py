import pytest

from cite_nexus_mcp.identifiers import normalize_doi, parse_identifier


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("https://doi.org/10.1234/ABC", "doi:10.1234/abc"),
        ("DOI:10.1234/a(b)", "doi:10.1234/a(b)"),
        ("https://arxiv.org/pdf/1706.03762v5.pdf", "arxiv:1706.03762"),
        ("arXiv:hep-th/9901001v2", "arxiv:hep-th/9901001"),
        ("PMID:12345678", "pmid:12345678"),
        ("https://pubmed.ncbi.nlm.nih.gov/12345678/", "pmid:12345678"),
        ("PMC12345", "pmcid:PMC12345"),
        ("https://openalex.org/W12345678", "openalex:W12345678"),
        ("scholar:123456789", "scholar:123456789"),
        ("WOS:000123456789", "wos:000123456789"),
        ("scopus:987654321", "scopus:987654321"),
        ("europe_pmc:MED:12345678", "europe_pmc:MED:12345678"),
    ],
)
def test_identifiers_round_trip(text, canonical):
    parsed = parse_identifier(text)
    assert parsed and parsed.canonical == canonical
    assert parse_identifier(canonical) == parsed


@pytest.mark.parametrize(
    "text",
    [
        "",
        "123456789",
        "a plausible paper title",
        "https://localhost/secret",
        "https://example.org/10.1234/x",
    ],
)
def test_ambiguous_or_arbitrary_urls_are_not_resolved(text):
    assert parse_identifier(text) is None


def test_doi_punctuation():
    assert normalize_doi("(10.1234/ABC(def)).") == "10.1234/abc(def)"
    assert normalize_doi("https://doi.org/10.1234%2FABC") == "10.1234/abc"


def test_doi_url_tracking_parameters_are_not_part_of_identifier():
    assert (
        parse_identifier("https://doi.org/10.1234/example?utm_source=test").canonical
        == "doi:10.1234/example"
    )
