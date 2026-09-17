"""Scholarly graph APIs with explicit coverage and access requirements."""

from typing import Any
from urllib.parse import quote

from ..config import secret
from ..http import ProviderError
from ..identifiers import Identifier
from ..models import AccessLocation, Author, Metric, Paper
from .base import Page, Provider, clean, integer


class SemanticScholar(Provider):
    id = "semantic_scholar"
    name = "Semantic Scholar"
    description = "Academic Graph search, citation counts and graph traversal; optional key, shared anonymous rate limits."
    documentation = "https://api.semanticscholar.org/api-docs/graph"
    kinds = ("doi", "arxiv", "pmid", "pmcid", "semantic_scholar")
    capabilities = ("search", "resolve", "citations", "references")
    root = "https://api.semanticscholar.org/graph/v1/paper"
    fields = "paperId,externalIds,title,authors,year,publicationDate,venue,publicationTypes,journal,abstract,url,citationCount,openAccessPdf,isOpenAccess"

    def headers(self) -> dict[str, str]:
        key = secret(self.settings.semantic_scholar_api_key)
        return {"x-api-key": key} if key else {}

    @staticmethod
    def lookup(identifier: Identifier) -> str:
        prefixes = {"doi": "DOI", "arxiv": "ARXIV", "pmid": "PMID", "pmcid": "PMCID"}
        return (
            f"{prefixes[identifier.kind]}:{identifier.value}"
            if identifier.kind in prefixes
            else identifier.value
        )

    def parse(self, data: dict[str, Any]) -> Paper:
        record_id = data["paperId"]
        ids = data.get("externalIds") or {}
        pdf = data.get("openAccessPdf") or {}
        journal = data.get("journal") or {}
        count = integer(data.get("citationCount"))
        return self.paper(
            record_id,
            f"https://www.semanticscholar.org/paper/{record_id}",
            identifiers={
                "semantic_scholar": record_id,
                "semantic_scholar_corpus": ids.get("CorpusId"),
                "doi": ids.get("DOI"),
                "arxiv": ids.get("ArXiv"),
                "pmid": ids.get("PubMed"),
                "pmcid": ids.get("PubMedCentral"),
            },
            title=data.get("title"),
            authors=[Author(name=a["name"]) for a in data.get("authors", [])],
            year=integer(data.get("year")),
            publication_date=data.get("publicationDate"),
            venue=clean(journal.get("name") or data.get("venue")),
            volume=journal.get("volume"),
            pages=journal.get("pages"),
            type="journal-article"
            if "JournalArticle" in (data.get("publicationTypes") or [])
            else "other",
            abstract=clean(data.get("abstract")),
            url=data.get("url"),
            metrics=[Metric(provider=self.id, count=count)] if count is not None else [],
            access=[
                AccessLocation(
                    url=pdf["url"],
                    provider=self.id,
                    is_open=data.get("isOpenAccess"),
                    license=pdf.get("license"),
                )
            ]
            if pdf.get("url")
            else [],
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        data = await self.http.json(
            self.id,
            f"{self.root}/search",
            params={"query": query, "limit": limit, "offset": offset, "fields": self.fields},
            headers=self.headers(),
            interval=1,
        )
        return Page([self.parse(item) for item in data.get("data", [])], integer(data.get("next")))

    async def resolve(self, identifier: Identifier) -> Paper:
        data = await self.http.json(
            self.id,
            f"{self.root}/{quote(self.lookup(identifier), safe='')}",
            params={"fields": self.fields},
            headers=self.headers(),
            interval=1,
        )
        return self.parse(data)

    async def graph(self, identifier: Identifier, direction: str, limit: int, offset: int) -> Page:
        data = await self.http.json(
            self.id,
            f"{self.root}/{quote(self.lookup(identifier), safe='')}/{direction}",
            params={"fields": self.fields, "limit": limit, "offset": offset},
            headers=self.headers(),
            interval=1,
        )
        key = "citingPaper" if direction == "citations" else "citedPaper"
        papers = [
            self.parse(item[key])
            for item in data.get("data", [])
            if item.get(key, {}).get("paperId")
        ]
        return Page(papers, integer(data.get("next")))


class OpenAlex(Provider):
    id = "openalex"
    name = "OpenAlex"
    access = "free credits / metered"
    description = "Multidisciplinary research graph; API key required by CiteNexus for predictable metered access."
    documentation = "https://developers.openalex.org/"
    required_env = ("OPENALEX_API_KEY",)
    credential = "openalex_api_key"
    kinds = ("doi", "pmid", "openalex")
    capabilities = ("search", "resolve", "citations", "references")
    root = "https://api.openalex.org/works"

    def params(self, **kwargs: Any) -> dict[str, Any]:
        self.require()
        kwargs["api_key"] = secret(self.settings.openalex_api_key)
        return kwargs

    def parse(self, data: dict[str, Any]) -> Paper:
        record_id = data["id"].rsplit("/", 1)[-1]
        ids = data.get("ids") or {}
        location = data.get("primary_location") or {}
        source = location.get("source") or {}
        biblio = data.get("biblio") or {}
        authors = [
            Author(name=a["author"]["display_name"], orcid=a["author"].get("orcid"))
            for a in data.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        abstract = None
        if index := data.get("abstract_inverted_index"):
            words = {
                i: word
                for word, positions in index.items()
                for i in positions
                if isinstance(i, int) and 0 <= i < 50000
            }
            abstract = " ".join(words[i] for i in sorted(words))
        access = []
        for loc in data.get("locations", []):
            url = loc.get("pdf_url") or loc.get("landing_page_url")
            if url:
                access.append(
                    AccessLocation(
                        url=url,
                        provider=self.id,
                        is_open=loc.get("is_oa"),
                        version=loc.get("version"),
                        license=loc.get("license"),
                    )
                )
        count = integer(data.get("cited_by_count"))
        pages = "-".join(filter(None, [biblio.get("first_page"), biblio.get("last_page")])) or None
        return self.paper(
            record_id,
            f"{self.root}/{record_id}",
            identifiers={
                "openalex": record_id,
                "doi": data.get("doi"),
                "pmid": ids.get("pmid", "").rsplit("/", 1)[-1],
            },
            title=data.get("display_name") or data.get("title"),
            authors=authors,
            authors_complete=not data.get("is_authors_truncated", False),
            year=integer(data.get("publication_year")),
            publication_date=data.get("publication_date"),
            type=data.get("type", "other"),
            venue=clean(source.get("display_name")),
            publisher=clean(source.get("host_organization_name")),
            volume=biblio.get("volume"),
            issue=biblio.get("issue"),
            pages=pages,
            abstract=abstract,
            url=location.get("landing_page_url") or data.get("id"),
            metrics=[Metric(provider=self.id, count=count)] if count is not None else [],
            is_retracted=data.get("is_retracted"),
            access=access,
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        data = await self.http.json(
            self.id,
            self.root,
            params=self.params(**{"search": query, "per-page": limit, "page": offset // limit + 1}),
        )
        papers = [self.parse(item) for item in data.get("results", [])]
        total = integer(data.get("meta", {}).get("count")) or 0
        return Page(papers, offset + limit if offset + limit < total else None)

    async def resolve(self, identifier: Identifier) -> Paper:
        key = {"doi": "https://doi.org/", "pmid": "pmid:", "openalex": ""}[
            identifier.kind
        ] + identifier.value
        data = await self.http.json(
            self.id, f"{self.root}/{quote(key, safe='')}", params=self.params()
        )
        return self.parse(data)

    async def graph(self, identifier: Identifier, direction: str, limit: int, offset: int) -> Page:
        paper = await self.resolve(identifier)
        key = paper.identifiers["openalex"]
        # OpenAlex's `cited_by` filter selects references made by this work.
        filter_name = "cites" if direction == "citations" else "cited_by"
        data = await self.http.json(
            self.id,
            self.root,
            params=self.params(
                **{"filter": f"{filter_name}:{key}", "per-page": limit, "page": offset // limit + 1}
            ),
        )
        if "results" not in data:
            raise ProviderError(self.id, "invalid_response", "Missing graph results.")
        papers = [self.parse(item) for item in data["results"]]
        total = integer(data.get("meta", {}).get("count")) or 0
        return Page(papers, offset + limit if offset + limit < total else None)
