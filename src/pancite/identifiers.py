"""Parse identifiers, never fetch arbitrary user-supplied URLs."""

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"]+", re.I)
ARXIV = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", re.I)


@dataclass(frozen=True)
class Identifier:
    kind: str
    value: str

    @property
    def canonical(self) -> str:
        return f"{self.kind}:{self.value}"


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith(("https://", "http://")) and urlparse(value).hostname in {
        "doi.org",
        "dx.doi.org",
    }:
        value = urlparse(value).path.lstrip("/")
    match = DOI.search(unquote(value))
    if not match:
        return None
    doi = match.group().rstrip(".,;")
    # Strip citation delimiters without damaging balanced DOI suffix parentheses.
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1]
    doi = doi.rstrip("}]")
    return doi.lower()


def parse_identifier(text: str) -> Identifier | None:
    text = unquote(text.strip())
    if not text or len(text) > 2000:
        return None
    doi = normalize_doi(text)
    if doi and (
        text.lower().startswith(
            ("10.", "doi:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/")
        )
    ):
        return Identifier("doi", doi)
    candidate = re.sub(r"^arxiv:\s*", "", text, flags=re.I)
    if text.startswith(("https://", "http://")):
        url = urlparse(text)
        host = (url.hostname or "").lower()
        if host in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
            candidate = re.sub(r"^/(abs|pdf)/", "", url.path).removesuffix(".pdf")
        elif host == "pubmed.ncbi.nlm.nih.gov":
            candidate = "pmid:" + url.path.strip("/")
        elif host == "pmc.ncbi.nlm.nih.gov":
            candidate = url.path.strip("/").removeprefix("articles/")
        elif host in {"openalex.org", "api.openalex.org"}:
            candidate = url.path.strip("/")
    if ARXIV.fullmatch(candidate):
        return Identifier("arxiv", re.sub(r"v\d+$", "", candidate, flags=re.I))
    patterns = {
        "pmid": r"pmid:\s*(\d+)",
        "pmcid": r"(?:pmcid:)?(PMC\d+)",
        "openalex": r"(?:openalex:)?(W\d+)",
        "semantic_scholar": r"(?:s2:|semantic_scholar:)([a-f0-9]{40}|CorpusId:\d+)",
        "scholar": r"scholar:(\d+)",
        "scopus": r"scopus:(?:SCOPUS_ID:)?(\d+)",
        "wos": r"(?:wos:)([a-z0-9]+)",
        "europe_pmc": r"europe_pmc:([A-Z]+:[A-Za-z0-9.-]+)",
    }
    for kind, pattern in patterns.items():
        if match := re.fullmatch(pattern, candidate, re.I):
            value = match[1]
            if kind in {"pmcid", "openalex"}:
                value = value.upper()
            return Identifier(kind, value)
    return None


def title_key(title: str) -> str:
    return " ".join(re.findall(r"\w+", title.casefold()))
