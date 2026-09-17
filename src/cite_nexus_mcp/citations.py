"""Deterministic exports from observed metadata. No model-generated facts."""

import hashlib
import json
import re
import unicodedata
from typing import Any, Literal

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.latexenc import latex_to_unicode

from .models import CitationResult, EnhancementResult, Paper

CitationFormat = Literal["bibtex", "ris", "csl-json"]


def bibtex_text(value: str) -> str:
    """Decode literal escapes and common LaTeX accents for source comparisons."""
    value = (
        value.replace(r"\textbackslash{}", "\\")
        .replace(r"\textasciitilde{}", "~")
        .replace(r"\textasciicircum{}", "^")
    )
    value = re.sub(r"\\([{}&%_#$])", r"\1", value)
    return latex_to_unicode(value)


def warnings(paper: Paper) -> list[str]:
    result = list(paper.warnings)
    if not paper.authors:
        result.append("The source did not supply authors; none were invented.")
    if not paper.authors_complete:
        result.append("The source author list may be incomplete; verify it before publication.")
    if paper.year is None:
        result.append("The source did not supply a publication year.")
    if paper.is_retracted:
        result.append("A provider marks this work as retracted; inspect the publisher's notice.")
    return list(dict.fromkeys(result))


def citation_key(paper: Paper) -> str:
    author = (
        (paper.authors[0].family or paper.authors[0].name.split()[-1])
        if paper.authors and paper.authors[0].name.split()
        else "anon"
    )
    word = paper.title.split()[0] if paper.title.split() else "work"
    raw = f"{author}{paper.year or 'nd'}{word}"
    key = re.sub(
        r"[^a-zA-Z0-9]", "", unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    ).lower()
    return (key or "work") + hashlib.sha256(paper.id.encode()).hexdigest()[:6]


def tex(value: str) -> str:
    escapes = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(escapes.get(c, c) for c in " ".join(value.split()))


def bibtex(paper: Paper) -> str:
    entry_type = {
        "journal-article": "article",
        "article": "article",
        "journalarticle": "article",
        "proceedings-article": "inproceedings",
        "paper-conference": "inproceedings",
        "book": "book",
        "book-chapter": "incollection",
        "dissertation": "phdthesis",
    }.get(paper.type, "misc")
    fields: dict[str, str] = {"title": "{" + tex(paper.title) + "}"}
    if paper.authors:
        names = []
        for author in paper.authors:
            if author.family:
                names.append(
                    tex(author.family) + (", " + tex(author.given) if author.given else "")
                )
            else:
                # A display name is not sufficient evidence to infer given/family names.
                names.append("{" + tex(author.name) + "}")
        if not paper.authors_complete:
            names.append("others")
        fields["author"] = " and ".join(names)
    if paper.year is not None:
        fields["year"] = str(paper.year)
    if paper.venue:
        key = (
            "journal"
            if entry_type == "article"
            else "booktitle"
            if entry_type in {"inproceedings", "incollection"}
            else "howpublished"
        )
        fields[key] = tex(paper.venue)
    for key, value in {
        "publisher": paper.publisher,
        "volume": paper.volume,
        "number": paper.issue,
        "pages": paper.pages,
        "doi": paper.identifiers.get("doi"),
        "url": paper.url,
    }.items():
        if value:
            fields[key] = tex(value)
    if arxiv := paper.identifiers.get("arxiv"):
        fields.update(eprint=arxiv, archivePrefix="arXiv")
    body = ",\n".join(f"  {key} = {{{value}}}" for key, value in fields.items())
    return f"@{entry_type}{{{citation_key(paper)},\n{body}\n}}"


def csl(paper: Paper) -> dict[str, Any]:
    entry_type = {
        "journal-article": "article-journal",
        "journalarticle": "article-journal",
        "article": "article-journal",
        "proceedings-article": "paper-conference",
        "book": "book",
        "book-chapter": "chapter",
        "dataset": "dataset",
        "software": "software",
        "dissertation": "thesis",
    }.get(paper.type, "article")
    result: dict[str, Any] = {"id": citation_key(paper), "type": entry_type, "title": paper.title}
    if paper.authors:
        result["author"] = [
            (
                {"family": a.family, **({"given": a.given} if a.given else {})}
                if a.family
                else {"literal": a.name}
            )
            for a in paper.authors
        ]
    if paper.year:
        result["issued"] = {"date-parts": [[paper.year]]}
    for key, value in {
        "container-title": paper.venue,
        "publisher": paper.publisher,
        "volume": paper.volume,
        "issue": paper.issue,
        "page": paper.pages,
        "DOI": paper.identifiers.get("doi"),
        "URL": paper.url,
        "abstract": paper.abstract,
    }.items():
        if value:
            result[key] = value
    return result


def ris(paper: Paper) -> str:
    kind = {
        "journal-article": "JOUR",
        "article": "JOUR",
        "journalarticle": "JOUR",
        "proceedings-article": "CPAPER",
        "book": "BOOK",
        "book-chapter": "CHAP",
        "dataset": "DATA",
        "software": "COMP",
        "dissertation": "THES",
    }.get(paper.type, "GEN")
    fields = [("TY", kind), ("ID", citation_key(paper)), ("TI", paper.title)]
    fields += [
        ("AU", f"{a.family}, {a.given}" if a.family and a.given else a.name) for a in paper.authors
    ]
    fields += [("PY", str(paper.year))] if paper.year else []
    fields += [
        (key, value)
        for key, value in {
            "JO": paper.venue,
            "PB": paper.publisher,
            "VL": paper.volume,
            "IS": paper.issue,
            "SP": paper.pages,
            "DO": paper.identifiers.get("doi"),
            "UR": paper.url,
            "AB": paper.abstract,
        }.items()
        if value
    ]
    # One metadata field per line; embedded newlines cannot inject RIS records.
    return "\n".join(f"{key}  - {' '.join(value.split())}" for key, value in fields) + "\nER  -\n"


def format_citation(paper: Paper, format: CitationFormat = "bibtex") -> CitationResult:
    if not paper.title.strip() or paper.title == "[Title unavailable]":
        raise ValueError("Cannot export a citation without a source-supplied title.")
    if format == "bibtex":
        citation = bibtex(paper)
    elif format == "ris":
        citation = ris(paper)
    elif format == "csl-json":
        citation = json.dumps(csl(paper), ensure_ascii=False, indent=2)
    else:
        raise ValueError("format must be bibtex, ris, or csl-json.")
    return CitationResult(format=format, citation=citation, paper=paper, warnings=warnings(paper))


def parse_bibtex(text: str) -> Any:
    if len(text) > 100_000:
        raise ValueError("BibTeX input exceeds 100,000 characters.")
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    try:
        database = bibtexparser.loads(text, parser=parser)
    except Exception:
        raise ValueError("Invalid BibTeX. Check braces, quotes, and string definitions.") from None
    if not database.entries or database.comments:
        raise ValueError("Expected complete BibTeX entries without unparsed text.")
    keys = [entry["ID"] for entry in database.entries]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate BibTeX citation keys; assign unique keys before normalizing.")
    return database


def enhance(text: str, template: str = "default") -> EnhancementResult:
    if template not in {"default", "compact"}:
        raise ValueError(
            "Supported templates: default, compact. Use a CSL processor for journal styles; free-form AI enrichment is no longer applied to bibliographic facts."
        )
    database = parse_bibtex(text)
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = None
    if template == "compact":
        writer.entry_separator = ""
    return EnhancementResult(
        bibtex=bibtexparser.dumps(database, writer=writer).strip(),
        warnings=[
            "Formatting normalized only. Metadata was preserved, not verified or inferred; use verify-citation to check it against sources."
        ],
    )
