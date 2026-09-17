"""Biomedical literature and arXiv, including source-native identifiers."""

from typing import Any
from urllib.parse import quote

from defusedxml.ElementTree import fromstring

from ..http import ProviderError
from ..identifiers import Identifier, parse_identifier
from ..models import AccessLocation, Author, Metric, Paper
from .base import Page, Provider, clean, integer


class EuropePMC(Provider):
    id = "europe_pmc"
    name = "Europe PMC"
    description = "Biomedical literature including PubMed and PMC; references, citations and open-access links."
    documentation = "https://europepmc.org/RestfulWebService"
    kinds = ("doi", "pmid", "pmcid", "europe_pmc")
    capabilities = ("search", "resolve", "citations", "references")
    root = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    def parse(self, data: dict[str, Any]) -> Paper:
        source = data.get("source", "MED")
        record_id = data.get("id", "")
        journal = data.get("journalInfo") or {}
        authors = [
            Author(
                name=a.get("fullName")
                or " ".join(filter(None, [a.get("firstName"), a.get("lastName")]))
                or a.get("collectiveName", "[Unnamed author]"),
                given=a.get("firstName"),
                family=a.get("lastName"),
            )
            for a in (data.get("authorList") or {}).get("author", [])
        ]
        if not authors and data.get("authorString"):
            authors = [
                Author(name=n.strip())
                for n in data["authorString"].rstrip(".").split(",")
                if n.strip()
            ]
        count = integer(data.get("citedByCount"))
        access = []
        for loc in (data.get("fullTextUrlList") or {}).get("fullTextUrl", []):
            if loc.get("url"):
                access.append(
                    AccessLocation(
                        url=loc["url"],
                        provider=self.id,
                        is_open=loc.get("availabilityCode") == "OA",
                    )
                )
        # A PMC identifier alone is not evidence that the work has an OA licence.
        if data.get("pmcid") and data.get("isOpenAccess") == "Y":
            access.append(
                AccessLocation(
                    url=f"https://pmc.ncbi.nlm.nih.gov/articles/{data['pmcid']}/",
                    provider=self.id,
                    is_open=True,
                )
            )
        return self.paper(
            f"{source}:{record_id}",
            f"https://europepmc.org/article/{source}/{record_id}",
            identifiers={
                "doi": data.get("doi"),
                "pmid": data.get("pmid") or (record_id if source == "MED" else None),
                "pmcid": data.get("pmcid"),
                "europe_pmc": f"{source}:{record_id}",
            },
            title=data.get("title"),
            authors=authors,
            authors_complete=bool(data.get("authorList")),
            year=integer(data.get("pubYear")),
            publication_date=data.get("firstPublicationDate"),
            venue=clean((journal.get("journal") or {}).get("title") or data.get("journalTitle")),
            volume=journal.get("volume"),
            issue=journal.get("issue"),
            pages=data.get("pageInfo"),
            type="journal-article",
            abstract=clean(data.get("abstractText")),
            url=f"https://europepmc.org/article/{source}/{record_id}",
            metrics=[Metric(provider=self.id, count=count)] if count is not None else [],
            is_retracted=True if data.get("isRetracted") == "Y" else None,
            access=access,
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        if offset:
            raise ProviderError(
                self.id,
                "invalid_pagination",
                "Europe PMC search uses cursors. Pass its next_cursors token as cursor with this provider selected alone.",
            )
        return await self.search_cursor(query, limit, "*")

    async def search_cursor(self, query: str, limit: int, cursor: str) -> Page:
        data = await self.http.json(
            self.id,
            f"{self.root}/search",
            params={
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": limit,
                "cursorMark": cursor,
            },
        )
        papers = [self.parse(item) for item in data.get("resultList", {}).get("result", [])]
        total = integer(data.get("hitCount")) or 0
        next_cursor = data.get("nextCursorMark")
        return Page(
            papers,
            next_cursor=next_cursor
            if papers and next_cursor != cursor and total > len(papers)
            else None,
        )

    async def resolve(self, identifier: Identifier) -> Paper:
        if identifier.kind == "europe_pmc":
            source, record_id = identifier.value.split(":", 1)
            query = f"EXT_ID:{record_id} AND SRC:{source}"
        else:
            field = {"doi": "DOI", "pmid": "EXT_ID", "pmcid": "PMCID"}[identifier.kind]
            query = f'{field}:"{identifier.value}"'
            if identifier.kind == "pmid":
                query = f"EXT_ID:{identifier.value} AND SRC:MED"
        page = await self.search(query, 1, 0)
        if not page.papers:
            raise ProviderError(self.id, "not_found", "Record was not found.")
        return page.papers[0]

    async def graph(self, identifier: Identifier, direction: str, limit: int, offset: int) -> Page:
        paper = await self.resolve(identifier)
        source, record_id = paper.identifiers["europe_pmc"].split(":", 1)
        endpoint = "citations" if direction == "citations" else "references"
        data = await self.http.json(
            self.id,
            f"{self.root}/{source}/{quote(record_id, safe='')}/{endpoint}",
            params={"format": "json", "pageSize": limit, "page": offset // limit + 1},
        )
        key = "citation" if direction == "citations" else "reference"
        papers = [
            self.parse(item) for item in data.get(key + "List", {}).get(key, []) if item.get("id")
        ]
        total = integer(data.get("hitCount")) or 0
        return Page(papers, offset + limit if offset + limit < total else None)


class Arxiv(Provider):
    id = "arxiv"
    name = "arXiv"
    description = "Preprints in physics, mathematics, computer science and related fields; paced at one request per three seconds."
    documentation = "https://info.arxiv.org/help/api/user-manual.html"
    kinds = ("arxiv",)
    root = "https://export.arxiv.org/api/query"
    ns = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}

    def parse_feed(self, data: bytes) -> list[Paper]:
        root = fromstring(data)
        papers = []
        for entry in root.findall("a:entry", self.ns):
            url = entry.findtext("a:id", "", self.ns)
            parsed = parse_identifier(url)
            if parsed is None:
                if "errors" in url:
                    raise ProviderError(
                        self.id, "invalid_query", "arXiv rejected the search query."
                    )
                continue
            arxiv_id = parsed.value
            published = entry.findtext("a:published", "", self.ns)[:10]
            authors = [
                Author(name=a.findtext("a:name", "[Unnamed author]", self.ns))
                for a in entry.findall("a:author", self.ns)
            ]
            papers.append(
                self.paper(
                    arxiv_id,
                    f"https://arxiv.org/abs/{arxiv_id}",
                    identifiers={"arxiv": arxiv_id, "doi": entry.findtext("ar:doi", None, self.ns)},
                    title=entry.findtext("a:title", "", self.ns),
                    authors=authors,
                    year=integer(published[:4]),
                    publication_date=published or None,
                    type="preprint",
                    venue=clean(entry.findtext("ar:journal_ref", None, self.ns)),
                    abstract=clean(entry.findtext("a:summary", None, self.ns)),
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    access=[
                        AccessLocation(
                            url=f"https://arxiv.org/pdf/{arxiv_id}",
                            provider=self.id,
                            is_open=True,
                            version="submittedVersion",
                        )
                    ],
                    warnings=["Preprint metadata may differ from the published version."],
                )
            )
        return papers

    async def search(self, query: str, limit: int, offset: int) -> Page:
        search = (
            query
            if any(f"{f}:" in query for f in ("ti", "au", "abs", "cat", "all", "id"))
            else f"all:{query}"
        )
        data = await self.http.get(
            self.id,
            self.root,
            params={
                "search_query": search,
                "start": offset,
                "max_results": limit,
                "sortBy": "relevance",
            },
            interval=3,
        )
        papers = self.parse_feed(data)
        return Page(papers, offset + limit if len(papers) == limit else None)

    async def resolve(self, identifier: Identifier) -> Paper:
        data = await self.http.get(
            self.id, self.root, params={"id_list": identifier.value, "max_results": 1}, interval=3
        )
        papers = self.parse_feed(data)
        if not papers:
            raise ProviderError(self.id, "not_found", "Record was not found.")
        return papers[0]
