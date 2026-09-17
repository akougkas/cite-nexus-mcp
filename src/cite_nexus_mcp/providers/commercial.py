"""Optional vendor adapters. Calls require explicit selection or configured defaults."""

import json
import re
from typing import Any
from urllib.parse import quote

from ..config import secret
from ..http import ProviderError
from ..identifiers import Identifier
from ..models import Author, Metric, Paper
from .base import Page, Provider, clean, integer


class SerpAPI(Provider):
    id = "serpapi"
    name = "Google Scholar via SerpAPI"
    access = "commercial"
    description = "Vendor-mediated Google Scholar discovery. Snippets and partial author lists are explicitly marked."
    documentation = "https://serpapi.com/google-scholar-api"
    required_env = ("SERPAPI_API_KEY",)
    credential = "serpapi_api_key"
    kinds = ("scholar",)
    capabilities = ("search", "resolve", "citations")
    root = "https://serpapi.com/search.json"
    max_limit = 20

    def parse(self, data: dict[str, Any]) -> Paper:
        links = data.get("inline_links") or {}
        cited = links.get("cited_by") or {}
        versions = links.get("versions") or {}
        cluster = versions.get("cluster_id") or cited.get("cites_id")
        publication = data.get("publication_info") or {}
        years = re.findall(r"\b(?:19|20)\d{2}\b", publication.get("summary", ""))
        count = integer(cited.get("total"))
        record_id = str(cluster or data.get("result_id", "unknown"))
        return self.paper(
            record_id,
            f"https://scholar.google.com/scholar?cluster={cluster}"
            if cluster
            else "https://scholar.google.com/",
            identifiers={"scholar": str(cluster) if cluster else None},
            title=data.get("title"),
            authors=[
                Author(name=a["name"]) for a in publication.get("authors", []) if a.get("name")
            ],
            authors_complete=False,
            year=integer(years[-1]) if years else None,
            url=data.get("link"),
            metrics=[Metric(provider=self.id, count=count)] if count is not None else [],
            warnings=[
                "Google Scholar metadata can be incomplete; a snippet is not an abstract. Resolve a DOI with a metadata provider before citing."
            ],
        )

    async def request(self, **kwargs: Any) -> dict[str, Any]:
        self.require()
        data = await self.http.json(
            self.id,
            self.root,
            params={
                "engine": "google_scholar",
                "api_key": secret(self.settings.serpapi_api_key),
                **kwargs,
            },
        )
        if data.get("error"):
            raise ProviderError(
                self.id, "upstream_error", "SerpAPI returned an error; check query, quota and key."
            )
        return data

    async def search(self, query: str, limit: int, offset: int) -> Page:
        data = await self.request(q=query, num=min(limit, 20), start=offset)
        papers = [self.parse(item) for item in data.get("organic_results", [])]
        return Page(
            papers,
            offset + min(limit, 20) if data.get("serpapi_pagination", {}).get("next") else None,
        )

    async def resolve(self, identifier: Identifier) -> Paper:
        data = await self.request(cluster=identifier.value, num=1)
        results = data.get("organic_results", [])
        if not results:
            raise ProviderError(self.id, "not_found", "Scholar cluster was not found.")
        paper = self.parse(results[0])
        # The request cluster is authoritative even when the result has no inline links.
        paper.identifiers["scholar"] = identifier.value
        paper.id = identifier.canonical
        return paper

    async def graph(self, identifier: Identifier, direction: str, limit: int, offset: int) -> Page:
        if direction != "citations":
            return await super().graph(identifier, direction, limit, offset)
        data = await self.request(cites=identifier.value, num=min(limit, 20), start=offset)
        papers = [self.parse(item) for item in data.get("organic_results", [])]
        return Page(
            papers,
            offset + min(limit, 20) if data.get("serpapi_pagination", {}).get("next") else None,
        )


class Scopus(Provider):
    id = "scopus"
    name = "Elsevier Scopus"
    access = "institutional / commercial"
    description = "Curated multidisciplinary abstracts and citations; results depend on key, network and subscription entitlement."
    documentation = "https://dev.elsevier.com/documentation/ScopusSearchAPI.wadl"
    required_env = ("SCOPUS_API_KEY",)
    credential = "scopus_api_key"
    kinds = ("doi", "scopus")
    root = "https://api.elsevier.com/content/search/scopus"

    def headers(self) -> dict[str, str]:
        self.require()
        headers = {
            "X-ELS-APIKey": secret(self.settings.scopus_api_key) or "",
            "Accept": "application/json",
        }
        if token := secret(self.settings.scopus_insttoken):
            headers["X-ELS-Insttoken"] = token
        return headers

    def parse(self, data: dict[str, Any]) -> Paper:
        record_id = data.get("dc:identifier", "").removeprefix("SCOPUS_ID:")
        count = integer(data.get("citedby-count"))
        cover = data.get("prism:coverDate", "")
        authors = [
            Author(
                name=a.get("authname") or a.get("surname", "[Unnamed author]"),
                family=a.get("surname"),
                given=a.get("given-name"),
            )
            for a in data.get("author", [])
        ]
        if not authors and data.get("dc:creator"):
            authors = [Author(name=data["dc:creator"])]
        url = next(
            (link.get("@href") for link in data.get("link", []) if link.get("@ref") == "scopus"),
            None,
        )
        return self.paper(
            record_id,
            f"https://api.elsevier.com/content/abstract/scopus_id/{record_id}",
            identifiers={"scopus": record_id, "doi": data.get("prism:doi")},
            title=data.get("dc:title"),
            authors=authors,
            authors_complete=bool(data.get("author")),
            year=integer(cover[:4]),
            publication_date=cover or None,
            venue=clean(data.get("prism:publicationName")),
            volume=data.get("prism:volume"),
            issue=data.get("prism:issueIdentifier"),
            pages=data.get("prism:pageRange"),
            type="journal-article" if data.get("prism:aggregationType") == "Journal" else "other",
            url=url,
            metrics=[Metric(provider=self.id, count=count)] if count is not None else [],
            warnings=[]
            if data.get("author")
            else ["Scopus search supplied only the lead author; the author list is incomplete."],
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        if not re.search(r"\b[A-Z][A-Z0-9-]*\s*\(", query, re.I):
            query = f"TITLE-ABS-KEY({json.dumps(query, ensure_ascii=False)})"
        data = await self.http.json(
            self.id,
            self.root,
            params={"query": query, "count": limit, "start": offset, "view": "STANDARD"},
            headers=self.headers(),
        )
        results = data.get("search-results")
        if results is None:
            raise ProviderError(
                self.id, "invalid_response", "Missing Scopus search results; check entitlement."
            )
        papers = [
            self.parse(item) for item in results.get("entry", []) if item.get("dc:identifier")
        ]
        total = integer(results.get("opensearch:totalResults")) or 0
        return Page(papers, offset + limit if offset + limit < total else None)

    async def resolve(self, identifier: Identifier) -> Paper:
        field = "DOI" if identifier.kind == "doi" else "SCOPUS-ID"
        page = await self.search(f'{field}("{identifier.value}")', 1, 0)
        if not page.papers:
            raise ProviderError(self.id, "not_found", "Record was not found.")
        return page.papers[0]


class WebOfScience(Provider):
    id = "wos"
    name = "Clarivate Web of Science Starter"
    access = "institutional / commercial"
    description = (
        "Curated Web of Science records; citation counts and quotas depend on subscription."
    )
    documentation = "https://developer.clarivate.com/apis/wos-starter"
    required_env = ("WOS_API_KEY",)
    credential = "wos_api_key"
    kinds = ("doi", "wos")
    root = "https://api.clarivate.com/apis/wos-starter/v1/documents"

    def headers(self) -> dict[str, str]:
        self.require()
        return {"X-ApiKey": secret(self.settings.wos_api_key) or ""}

    def parse(self, data: dict[str, Any]) -> Paper:
        record_id = data["uid"].removeprefix("WOS:")
        source = data.get("source") or {}
        identifiers = data.get("identifiers") or {}
        authors = [
            Author(name=a.get("displayName") or a.get("wosStandard", "[Unnamed author]"))
            for a in (data.get("names") or {}).get("authors", [])
        ]
        return self.paper(
            record_id,
            f"{self.root}/WOS:{record_id}",
            identifiers={
                "wos": record_id,
                "doi": identifiers.get("doi"),
                "pmid": identifiers.get("pmid"),
            },
            title=data.get("title"),
            authors=authors,
            year=integer(source.get("publishYear")),
            venue=clean(source.get("sourceTitle")),
            volume=source.get("volume"),
            issue=source.get("issue"),
            pages=(source.get("pages") or {}).get("range"),
            url=(data.get("links") or {}).get("record"),
            metrics=[
                Metric(provider=self.id, count=c["count"], scope=c.get("db", "WOS"))
                for c in data.get("citations", [])
                if isinstance(c.get("count"), int) and c["count"] >= 0
            ],
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        if not re.search(r"\b[A-Z]{2}\s*=", query, re.I):
            query = f"TS=({json.dumps(query, ensure_ascii=False)})"
        data = await self.http.json(
            self.id,
            self.root,
            params={"q": query, "limit": limit, "page": offset // limit + 1},
            headers=self.headers(),
        )
        papers = [self.parse(item) for item in data.get("hits", [])]
        total = integer(data.get("metadata", {}).get("total")) or 0
        return Page(papers, offset + limit if offset + limit < total else None)

    async def resolve(self, identifier: Identifier) -> Paper:
        if identifier.kind == "wos":
            data = await self.http.json(
                self.id,
                f"{self.root}/{quote('WOS:' + identifier.value, safe='')}",
                headers=self.headers(),
            )
            return self.parse(data)
        page = await self.search(f'DO=("{identifier.value}")', 1, 0)
        if not page.papers:
            raise ProviderError(self.id, "not_found", "Record was not found.")
        return page.papers[0]
