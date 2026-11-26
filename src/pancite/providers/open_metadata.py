"""Crossref and DataCite: free DOI metadata without a mandatory API key."""

from typing import Any
from urllib.parse import quote

from ..identifiers import Identifier
from ..models import Author, Metric, Paper
from .base import Page, Provider, clean, first, integer


class Crossref(Provider):
    id = "crossref"
    name = "Crossref"
    description = (
        "Publisher-deposited DOI metadata and citation counts; optional polite-pool email."
    )
    documentation = "https://www.crossref.org/documentation/retrieve-metadata/rest-api/"
    kinds = ("doi",)
    root = "https://api.crossref.org/works"

    def params(self, **kwargs: Any) -> dict[str, Any]:
        if self.settings.contact_email:
            kwargs["mailto"] = self.settings.contact_email
        return kwargs

    def parse(self, data: dict[str, Any]) -> Paper:
        doi = data.get("DOI", "")
        date = data.get("published") or data.get("issued") or {}
        parts = first(date.get("date-parts")) or []
        authors = [
            Author(
                name=clean(a.get("name"))
                or " ".join(filter(None, [a.get("given"), a.get("family")]))
                or "[Unnamed author]",
                given=a.get("given"),
                family=a.get("family"),
                orcid=a.get("ORCID"),
            )
            for a in data.get("author", [])
        ]
        count = integer(data.get("is-referenced-by-count"))
        updates = data.get("update-to", [])
        return self.paper(
            doi,
            f"{self.root}/{quote(doi, safe='')}",
            identifiers={"doi": doi},
            title=first(data.get("title")),
            authors=authors,
            year=integer(first(parts)),
            publication_date="-".join(str(p).zfill(4 if i == 0 else 2) for i, p in enumerate(parts))
            or None,
            venue=clean(first(data.get("container-title"))),
            publisher=clean(data.get("publisher")),
            type=data.get("type", "other"),
            volume=data.get("volume"),
            issue=data.get("issue"),
            pages=data.get("page") or data.get("article-number"),
            abstract=clean(data.get("abstract")),
            url=data.get("URL") or f"https://doi.org/{doi}",
            metrics=[Metric(provider=self.id, count=count)] if count is not None else [],
            warnings=["This record is an update/retraction notice; inspect the publisher record."]
            if any(u.get("type") == "retraction" for u in updates)
            else [],
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        data = await self.http.json(
            self.id,
            self.root,
            params=self.params(**{"query.bibliographic": query, "rows": limit, "offset": offset}),
        )
        message = data["message"]
        papers = [self.parse(item) for item in message.get("items", [])]
        total = integer(message.get("total-results")) or 0
        return Page(papers, offset + limit if offset + limit < total and papers else None)

    async def resolve(self, identifier: Identifier) -> Paper:
        data = await self.http.json(
            self.id, f"{self.root}/{quote(identifier.value, safe='')}", params=self.params()
        )
        return self.parse(data["message"])


class DataCite(Provider):
    id = "datacite"
    name = "DataCite"
    description = "Research datasets, software, preprints and other DOI-registered outputs."
    documentation = "https://support.datacite.org/docs/api"
    kinds = ("doi",)
    root = "https://api.datacite.org/dois"

    def parse(self, record: dict[str, Any]) -> Paper:
        data = record["attributes"]
        doi = data.get("doi", record.get("id", ""))
        authors = []
        for a in data.get("creators", []):
            orcid = next(
                (
                    i.get("nameIdentifier")
                    for i in a.get("nameIdentifiers", [])
                    if i.get("nameIdentifierScheme", "").lower() == "orcid"
                ),
                None,
            )
            authors.append(
                Author(
                    name=a.get("name")
                    or " ".join(filter(None, [a.get("givenName"), a.get("familyName")]))
                    or "[Unnamed author]",
                    given=a.get("givenName"),
                    family=a.get("familyName"),
                    orcid=orcid,
                )
            )
        container = data.get("container") or {}
        publisher = data.get("publisher")
        if isinstance(publisher, dict):
            publisher = publisher.get("name")
        return self.paper(
            doi,
            f"{self.root}/{quote(doi, safe='')}",
            identifiers={"doi": doi},
            title=(first(data.get("titles")) or {}).get("title"),
            authors=authors,
            year=integer(data.get("publicationYear")),
            type=(data.get("types") or {}).get("resourceTypeGeneral", "other").lower(),
            publisher=clean(publisher),
            venue=clean(container.get("title")),
            abstract=next(
                (
                    clean(d.get("description"))
                    for d in data.get("descriptions", [])
                    if d.get("descriptionType") == "Abstract"
                ),
                None,
            ),
            url=data.get("url") or f"https://doi.org/{doi}",
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        data = await self.http.json(
            self.id,
            self.root,
            params={"query": query, "page[size]": limit, "page[number]": offset // limit + 1},
        )
        papers = [self.parse(item) for item in data.get("data", [])]
        total = integer(data.get("meta", {}).get("total")) or 0
        return Page(papers, offset + limit if offset + limit < total and papers else None)

    async def resolve(self, identifier: Identifier) -> Paper:
        data = await self.http.json(self.id, f"{self.root}/{quote(identifier.value, safe='')}")
        return self.parse(data["data"])
