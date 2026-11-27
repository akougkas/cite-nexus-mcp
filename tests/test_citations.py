import json

import bibtexparser
import pytest

from pancite.citations import enhance, format_citation, read_reference
from pancite.config import Settings
from pancite.models import Author, Paper
from pancite.providers import registry


def test_bibtex_escapes_metadata_and_preserves_authors(records):
    paper = registry(None, Settings())["crossref"].parse(records["crossref"])
    paper.title = "GPU & AI: 50% of {data}_sets #1 $2"
    result = format_citation(paper)
    database = bibtexparser.loads(result.citation)
    assert len(database.entries) == 1
    entry = database.entries[0]
    assert entry["author"] == "Lovelace, Ada"
    assert r"\&" in entry["title"] and r"\%" in entry["title"] and r"\_" in entry["title"]
    assert entry["doi"] == "10.1234/example"
    assert entry["journal"] == "Research Journal"
    assert result == format_citation(paper)


def test_partial_author_list_is_not_presented_as_complete(records):
    paper = registry(None, Settings())["scopus"].parse(records["scopus"])
    result = format_citation(paper)
    assert " and others" in result.citation
    assert any("incomplete" in warning for warning in result.warnings)


def test_missing_fields_are_omitted_not_invented():
    paper = Paper(id="doi:10.1234/test", title="A measured result")
    result = format_citation(paper)
    assert "year =" not in result.citation and "author =" not in result.citation
    assert len(result.warnings) == 2
    paper.title = "[Title unavailable]"
    with pytest.raises(ValueError, match="source-supplied title"):
        format_citation(paper)


def test_csl_structured_names_and_corporate_names():
    paper = Paper(
        id="test",
        title="Work",
        authors=[
            Author(name="World Health Organization"),
            Author(name="Ada Lovelace", given="Ada", family="Lovelace"),
        ],
        year=2024,
        type="dataset",
    )
    csl = json.loads(format_citation(paper, "csl-json").citation)
    assert csl["author"] == [
        {"literal": "World Health Organization"},
        {"family": "Lovelace", "given": "Ada"},
    ]
    assert csl["type"] == "dataset"
    assert csl["issued"] == {"date-parts": [[2024]]}


def test_ris_prevents_metadata_record_injection():
    paper = Paper(id="test", title="Title\nER  -\nTY  - JOUR", year=2024)
    result = format_citation(paper, "ris").citation
    assert len([line for line in result.splitlines() if line.startswith("TY  -")]) == 1
    assert len([line for line in result.splitlines() if line.startswith("ER  -")]) == 1


def test_enhance_preserves_bibliographic_fields():
    text = "@article{key, title={GPU methods}, author={Lovelace, Ada}, year={2024}, note={Keep me}}"
    result = enhance(text)
    before = bibtexparser.loads(text).entries[0]
    after = bibtexparser.loads(result.bibtex).entries[0]
    assert after == before
    assert "keywords" not in after
    with pytest.raises(ValueError, match="Supported templates"):
        enhance(text, "infer awards")


@pytest.mark.parametrize(
    "text",
    [
        "not bibtex",
        "@article{broken, title={Unclosed}",
        "@article{a,title={One}}\n@article{a,title={Two}}",
    ],
)
def test_invalid_or_duplicate_bibtex_is_rejected(text):
    with pytest.raises(ValueError):
        enhance(text)


def test_read_reference_takes_one_record_from_ris_or_csl_json():
    ris = "TY  - JOUR\nT1  - Deep learning\nY1  - 2015/05/28\nDO  - 10.1038/nature14539\nER  -\n"
    csl = '{"DOI": "10.1038/nature14539", "title": "Deep learning", "issued": {"date-parts": [["2015"]]}}'
    expected = ("10.1038/nature14539", "Deep learning", 2015)
    assert read_reference("ris", ris) == expected
    assert read_reference("csl-json", f"[{csl}]") == expected
    assert read_reference("csl-json", '{"title": "Only a title"}') == ("Only a title", None, None)
    assert read_reference("text", "  10.1038/nature14539\n") == ("10.1038/nature14539", None, None)
    with pytest.raises(ValueError, match="one RIS record per call; the file has 2"):
        read_reference("ris", ris + ris)
    with pytest.raises(ValueError, match="one CSL-JSON item per call"):
        read_reference("csl-json", f"[{csl}, {csl}]")
    with pytest.raises(ValueError, match="neither a DOI nor a title"):
        read_reference("csl-json", '{"type": "book"}')
