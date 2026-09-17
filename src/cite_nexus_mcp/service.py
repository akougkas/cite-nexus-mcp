"""Research workflows, independent of MCP transport and client implementation."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from difflib import SequenceMatcher
from functools import partial
from typing import Any, Literal
from urllib.parse import quote

from .citations import CitationFormat, bibtex_text, format_citation, parse_bibtex
from .config import Settings
from .http import HTTP, ProviderError
from .identifiers import Identifier, normalize_doi, parse_identifier, title_key
from .models import (
    AccessLocation,
    AccessResult,
    BatchItem,
    BatchResult,
    CitationResult,
    GraphResult,
    MetricsResult,
    Paper,
    ProviderIssue,
    ProvidersResult,
    Resolution,
    SearchResult,
    VerificationResult,
)
from .providers import registry
from .providers.academic import EuropePMC
from .providers.base import Page, Provider

logger = logging.getLogger(__name__)
Progress = Callable[[int, int], Awaitable[None]]


def same_work(left: Paper, right: Paper) -> bool:
    preprints = {"preprint", "posted-content"}
    if (
        left.type != "other"
        and right.type != "other"
        and (left.type in preprints) != (right.type in preprints)
    ):
        return False
    # Conflicting persistent identifiers must never collapse just because titles match.
    shared = left.identifiers.keys() & right.identifiers.keys()
    if any(
        left.identifiers[key] != right.identifiers[key]
        for key in shared
        if key in {"doi", "arxiv", "pmid", "pmcid"}
    ):
        return False
    if any(left.identifiers[key] == right.identifiers[key] for key in shared):
        return True
    # With no shared identifier, require title, known year, and first-author agreement.
    if not left.authors or not right.authors or left.year is None or left.year != right.year:
        return False
    left_author = left.authors[0].family or left.authors[0].name
    right_author = right.authors[0].family or right.authors[0].name
    return (
        len(title_key(left.title)) >= 20
        and title_key(left.title) == title_key(right.title)
        and title_key(left_author) == title_key(right_author)
    )


def merge(left: Paper, right: Paper) -> Paper:
    result = left.model_copy(deep=True)
    result.identifiers.update(right.identifiers)
    for kind in right.identifiers:
        field = f"identifiers.{kind}"
        result.field_sources[field] = list(
            dict.fromkeys(result.field_sources.get(field, []) + right.field_sources.get(field, []))
        )
    if result.title == "[Title unavailable]" and right.title != "[Title unavailable]":
        result.title = right.title
        result.field_sources["title"] = right.field_sources.get("title", [])
    for field in (
        "year",
        "publication_date",
        "venue",
        "publisher",
        "volume",
        "issue",
        "pages",
        "abstract",
        "url",
    ):
        current, incoming = getattr(result, field), getattr(right, field)
        if current is None and incoming is not None:
            setattr(result, field, incoming)
            result.field_sources[field] = right.field_sources.get(field, [])
        elif (
            current is not None
            and incoming is not None
            and current != incoming
            and field in {"year", "venue"}
        ):
            result.warnings.append(
                f"Sources disagree on {field}: retained {current!r}; another reports {incoming!r}."
            )
    if not result.authors or (
        not result.authors_complete and right.authors_complete and right.authors
    ):
        result.authors = right.authors
        result.authors_complete = right.authors_complete
        result.field_sources["authors"] = right.field_sources.get("authors", [])
    if result.type == "other" and right.type != "other":
        result.type = right.type
        result.field_sources["type"] = right.field_sources.get("type", [])
    if right.is_retracted is not None:
        result.is_retracted = bool(result.is_retracted or right.is_retracted)
    if title_key(left.title) != title_key(right.title):
        result.warnings.append(f"Source titles differ; retained {left.title!r}.")
    result.sources += [
        s
        for s in right.sources
        if (s.provider, s.record_id) not in {(x.provider, x.record_id) for x in result.sources}
    ]
    result.metrics += [
        m
        for m in right.metrics
        if (m.provider, m.scope) not in {(x.provider, x.scope) for x in result.metrics}
    ]
    result.access += [
        a
        for a in right.access
        if (a.provider, a.url) not in {(x.provider, x.url) for x in result.access}
    ]
    result.warnings = list(dict.fromkeys(result.warnings + right.warnings))
    for kind in (
        "doi",
        "arxiv",
        "pmid",
        "pmcid",
        "openalex",
        "semantic_scholar",
        "scholar",
        "scopus",
        "wos",
    ):
        if kind in result.identifiers:
            result.id = f"{kind}:{result.identifiers[kind]}"
            break
    return result


def deduplicate(papers: list[Paper]) -> list[Paper]:
    merged: list[Paper] = []
    for paper in papers:
        for i, existing in enumerate(merged):
            if same_work(existing, paper):
                merged[i] = merge(existing, paper)
                break
        else:
            merged.append(paper)
    return merged


class ResearchService:
    def __init__(self, settings: Settings | None = None, http: HTTP | None = None):
        self.settings = settings or Settings.from_env()
        self.http = http or HTTP(self.settings)
        self.providers = registry(self.http, self.settings)
        unknown = set(self.settings.default_providers) - self.providers.keys()
        if unknown or not self.settings.default_providers:
            raise ValueError(
                "CITE_NEXUS_DEFAULT_PROVIDERS must contain known provider IDs: "
                + ", ".join(self.providers)
            )

    async def close(self) -> None:
        await self.http.close()

    def list_providers(self) -> ProvidersResult:
        return ProvidersResult(
            providers=[p.info() for p in self.providers.values()],
            policy="Defaults use public APIs without keys. Commercial and metered APIs run only when selected explicitly or named in CITE_NEXUS_DEFAULT_PROVIDERS. 'available' means credentials are configured, not that live access was tested.",
        )

    def select(self, names: list[str] | None) -> list[Provider]:
        selected = list(
            dict.fromkeys(names if names is not None else self.settings.default_providers)
        )
        if not selected:
            raise ValueError("Select at least one provider.")
        unknown = set(selected) - self.providers.keys()
        if unknown:
            raise ValueError("Unknown provider(s): " + ", ".join(sorted(unknown)))
        return [self.providers[name] for name in selected]

    async def attempt(
        self, provider: Provider, operation: Callable[[], Awaitable[Any]]
    ) -> Any | ProviderIssue:
        try:
            provider.require()
            async with asyncio.timeout(self.settings.operation_timeout):
                return await operation()
        except ProviderError as exc:
            return exc.issue
        except TimeoutError:
            return ProviderIssue(
                provider=provider.id,
                code="timeout",
                message="Provider exceeded the operation time budget.",
            )
        except Exception as exc:
            # Never expose upstream bodies or exception URLs: they can contain credentials.
            logger.warning("Provider %s failed normalization (%s)", provider.id, type(exc).__name__)
            return ProviderIssue(
                provider=provider.id,
                code="invalid_response",
                message="Provider returned an unexpected response shape.",
            )

    async def search(
        self,
        query: str,
        providers: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
        open_access_only: bool = False,
        include_abstract: bool = False,
        cursor: str | None = None,
    ) -> SearchResult:
        query = query.strip()
        if not query or len(query) > 2000:
            raise ValueError("Query must contain 1–2,000 characters.")
        if not 1 <= limit <= 50 or offset < 0 or offset > 10000 or offset % limit:
            raise ValueError("limit must be 1–50; offset must be 0–10,000 and a multiple of limit.")
        if year_from and year_to and year_from > year_to:
            raise ValueError("year_from must not be later than year_to.")
        selected = self.select(providers)
        if cursor is not None and (
            offset != 0
            or len(selected) != 1
            or not isinstance(selected[0], EuropePMC)
            or not 1 <= len(cursor) <= 4000
        ):
            raise ValueError(
                "cursor requires only europe_pmc, offset=0, and a 1–4,000 character token from next_cursors."
            )
        for provider in selected:
            if limit > provider.max_limit:
                raise ValueError(f"{provider.id} supports limit up to {provider.max_limit}.")
        operations = [
            partial(p.search_cursor, query, limit, cursor)
            if cursor is not None and isinstance(p, EuropePMC)
            else partial(p.search, query, limit, offset)
            for p in selected
        ]
        outcomes = await asyncio.gather(
            *(self.attempt(p, operation) for p, operation in zip(selected, operations, strict=True))
        )
        issues = [outcome for outcome in outcomes if isinstance(outcome, ProviderIssue)]
        pages = [
            (p.id, outcome)
            for p, outcome in zip(selected, outcomes, strict=True)
            if isinstance(outcome, Page)
        ]
        if not pages:
            raise ValueError(
                "All selected providers failed: "
                + "; ".join(f"{i.provider} [{i.code}]: {i.message}" for i in issues)
            )
        # Round-robin provider ranks: do not compare incompatible provider relevance scores.
        ordered = [
            page.papers[i] for i in range(limit) for _, page in pages if i < len(page.papers)
        ]
        papers = deduplicate(ordered)
        if year_from:
            papers = [p for p in papers if p.year is not None and p.year >= year_from]
        if year_to:
            papers = [p for p in papers if p.year is not None and p.year <= year_to]
        if open_access_only:
            papers = [p for p in papers if any(a.is_open for a in p.access)]
        if not include_abstract:
            for paper in papers:
                paper.abstract = None
                paper.field_sources.pop("abstract", None)
        result_warnings = [
            "Each provider contributes up to limit records. Results use provider-rank interleaving and conservative deduplication; this is not an exhaustive systematic review."
        ]
        if year_from or year_to or open_access_only:
            result_warnings.append(
                "Filters apply to the fetched page. Unknown year or open-access status is excluded; page further for more matches."
            )
        return SearchResult(
            query=query,
            papers=papers,
            providers=[p.id for p in selected],
            issues=issues,
            returned=len(papers),
            next_offsets={
                name: page.next_offset
                for name, page in pages
                if page.next_offset is not None and page.next_offset <= 10000
            },
            next_cursors={name: page.next_cursor for name, page in pages if page.next_cursor},
            warnings=result_warnings,
        )

    async def resolve(self, text: str, providers: list[str] | None = None) -> Resolution:
        try:
            async with asyncio.timeout(self.settings.operation_timeout):
                return await self._resolve(text, providers)
        except TimeoutError:
            raise ProviderError(
                "resolve", "timeout", "Identifier resolution exceeded the operation time budget."
            ) from None

    async def _resolve(self, text: str, providers: list[str] | None = None) -> Resolution:
        identifier = parse_identifier(text)
        if identifier is None:
            raise ValueError(
                "Use a DOI, arXiv ID, PMID:…, PMCID, OpenAlex W…, s2:…, scholar:…, scopus:… or WOS:… identifier. Use search-papers for titles."
            )
        if providers is not None:
            selected = self.select(providers)
        elif identifier.kind == "doi":
            selected = [self.providers[name] for name in ("crossref", "datacite", "europe_pmc")]
        else:
            defaults = {
                "arxiv": "arxiv",
                "pmid": "europe_pmc",
                "pmcid": "europe_pmc",
                "europe_pmc": "europe_pmc",
                "openalex": "openalex",
                "semantic_scholar": "semantic_scholar",
                "scholar": "serpapi",
                "scopus": "scopus",
                "wos": "wos",
            }
            selected = [self.providers[defaults[identifier.kind]]]
        issues = []
        result = None
        for provider in selected:
            if identifier.kind not in provider.kinds:
                issues.append(
                    ProviderIssue(
                        provider=provider.id,
                        code="unsupported_identifier",
                        message=f"Cannot resolve {identifier.kind} identifiers.",
                    )
                )
                continue
            outcome = await self.attempt(provider, partial(provider.resolve, identifier))
            if isinstance(outcome, ProviderIssue):
                issues.append(outcome)
                continue
            # A lookup endpoint is not enough: verify that its result contains the requested ID.
            actual = outcome.identifiers.get(identifier.kind)
            expected = identifier.value
            if identifier.kind == "semantic_scholar" and expected.lower().startswith("corpusid:"):
                corpus_id = outcome.identifiers.get("semantic_scholar_corpus")
                actual = f"CorpusId:{corpus_id}" if corpus_id else None
            if actual is None or actual.casefold() != expected.casefold():
                issues.append(
                    ProviderIssue(
                        provider=provider.id,
                        code="identifier_mismatch",
                        message="Lookup returned a different or missing identifier; record was rejected.",
                    )
                )
                continue
            if result is None:
                result = outcome
            elif same_work(result, outcome):
                result = merge(result, outcome)
            else:
                issues.append(
                    ProviderIssue(
                        provider=provider.id,
                        code="identifier_conflict",
                        message="Sources supplied conflicting identifiers; records were not merged.",
                    )
                )
            if providers is None:
                break
        if result is None:
            codes = {i.code for i in issues}
            code = "not_found" if codes and codes <= {"not_found"} else "unavailable"
            raise ProviderError(
                "resolve",
                code,
                "; ".join(f"{i.provider} [{i.code}]: {i.message}" for i in issues)
                or "No provider can resolve this identifier.",
            )
        return Resolution(identifier=identifier.canonical, paper=result, issues=issues)

    async def citation(
        self, identifier: str, format: CitationFormat = "bibtex", providers: list[str] | None = None
    ) -> CitationResult:
        resolved = await self.resolve(identifier, providers)
        result = format_citation(resolved.paper, format)
        result.warnings += [f"{i.provider} [{i.code}]: {i.message}" for i in resolved.issues]
        return result

    async def verify(
        self,
        citation: str,
        expected_title: str | None = None,
        expected_year: int | None = None,
        providers: list[str] | None = None,
    ) -> VerificationResult:
        identifier = parse_identifier(citation)
        if citation.lstrip().startswith("@"):
            database = parse_bibtex(citation)
            if len(database.entries) != 1:
                raise ValueError("Verify one BibTeX entry per call.")
            entry = database.entries[0]
            identifier = parse_identifier(bibtex_text(entry.get("doi") or entry.get("url") or ""))
            expected_title = expected_title or bibtex_text(entry.get("title", "")) or None
            year = entry.get("year", "")
            expected_year = expected_year or (int(year) if year.isdigit() else None)
        if identifier:
            try:
                resolved = await self.resolve(identifier.canonical, providers)
            except ProviderError as exc:
                return VerificationResult(
                    status="not_found" if exc.issue.code == "not_found" else "unavailable",
                    identifier=identifier.canonical,
                    issues=[exc.issue],
                    explanation="No matching source record could be retrieved. A provider failure is not evidence of a fabricated citation.",
                )
            differences = []
            if expected_title and title_key(expected_title) != title_key(resolved.paper.title):
                differences.append(
                    f"Title differs: supplied {expected_title!r}; source {resolved.paper.title!r}."
                )
            if expected_year is not None and resolved.paper.year != expected_year:
                differences.append(
                    f"Year differs or is unavailable: supplied {expected_year}; source {resolved.paper.year}."
                )
            return VerificationResult(
                status="mismatch" if differences else "verified",
                identifier=identifier.canonical,
                paper=resolved.paper,
                differences=differences,
                issues=resolved.issues,
                explanation="Verified identifier existence and any supplied title/year against retrieved metadata. This does not verify the paper's claims, full author list, or publication integrity.",
            )
        query = expected_title or citation.strip()
        try:
            search = await self.search(query, providers=providers, limit=5)
        except ValueError as exc:
            if not str(exc).startswith("All selected providers failed"):
                raise
            return VerificationResult(status="unavailable", explanation=str(exc))
        candidates = sorted(
            search.papers,
            key=lambda p: SequenceMatcher(None, title_key(query), title_key(p.title)).ratio(),
            reverse=True,
        )[:5]
        return VerificationResult(
            status="ambiguous" if candidates else "not_found",
            candidates=candidates,
            issues=search.issues,
            explanation="Title search produces candidates, not identity proof. Choose an identifier and verify it with the expected title and year.",
        )

    async def metrics(self, identifier: str, providers: list[str] | None = None) -> MetricsResult:
        resolved = await self.resolve(identifier, providers)
        return MetricsResult(
            paper=resolved.paper, metrics=resolved.paper.metrics, issues=resolved.issues
        )

    async def graph(
        self,
        identifier: str,
        direction: Literal["citations", "references"],
        provider: str = "semantic_scholar",
        limit: int = 10,
        offset: int = 0,
    ) -> GraphResult:
        if direction not in {"citations", "references"}:
            raise ValueError("direction must be citations or references.")
        if not 1 <= limit <= 50 or offset < 0 or offset > 10000 or offset % limit:
            raise ValueError("limit must be 1–50; offset must be 0–10,000 and a multiple of limit.")
        selected = self.select([provider])[0]
        if limit > selected.max_limit:
            raise ValueError(f"{provider} supports limit up to {selected.max_limit}.")
        if direction not in selected.capabilities:
            raise ValueError(f"{provider} does not support {direction}.")
        parsed = parse_identifier(identifier)
        if not parsed or parsed.kind not in selected.kinds:
            raise ValueError(
                f"Use an identifier supported by {provider}: {', '.join(selected.kinds)}."
            )
        outcome = await self.attempt(
            selected, lambda: selected.graph(parsed, direction, limit, offset)
        )
        if isinstance(outcome, ProviderIssue):
            raise ProviderError(
                outcome.provider, outcome.code, outcome.message, outcome.retry_after
            )
        return GraphResult(
            identifier=parsed.canonical,
            direction=direction,
            provider=provider,
            papers=outcome.papers,
            returned=len(outcome.papers),
            next_offset=outcome.next_offset,
            warnings=[
                "This page is a sample of the provider's graph, not the paper's total citation count."
            ],
        )

    async def open_access(
        self, identifier: str, providers: list[str] | None = None
    ) -> AccessResult:
        resolved = await self.resolve(identifier, providers)
        issues = list(resolved.issues)
        locations = [a for a in resolved.paper.access if a.is_open]
        doi = resolved.paper.identifiers.get("doi")
        if doi and self.settings.unpaywall_email:
            try:
                async with asyncio.timeout(self.settings.operation_timeout):
                    data = await self.http.json(
                        "unpaywall",
                        f"https://api.unpaywall.org/v2/{quote(doi, safe='')}",
                        params={"email": self.settings.unpaywall_email},
                    )
                if normalize_doi(data.get("doi")) != doi:
                    raise ProviderError(
                        "unpaywall", "identifier_mismatch", "Unpaywall returned a different DOI."
                    )
                for loc in data.get("oa_locations", []):
                    url = (
                        loc.get("url_for_pdf") or loc.get("url") or loc.get("url_for_landing_page")
                    )
                    if url:
                        locations.append(
                            AccessLocation(
                                url=url,
                                provider="unpaywall",
                                is_open=True,
                                version=loc.get("version"),
                                license=loc.get("license"),
                            )
                        )
            except ProviderError as exc:
                issues.append(exc.issue)
            except (TimeoutError, ValueError, TypeError, KeyError):
                issues.append(
                    ProviderIssue(
                        provider="unpaywall",
                        code="unavailable",
                        message="Could not retrieve open-access locations.",
                    )
                )
        elif doi and providers is None:
            # Free biomedical OA enrichment for DOI-first workflows.
            provider = self.providers["europe_pmc"]
            outcome = await self.attempt(provider, lambda: provider.resolve(Identifier("doi", doi)))
            if isinstance(outcome, Paper) and outcome.identifiers.get("doi") == doi:
                locations += [a for a in outcome.access if a.is_open]
            elif isinstance(outcome, ProviderIssue):
                issues.append(outcome)
        unique = {(a.provider, a.url): a for a in locations}
        return AccessResult(paper=resolved.paper, locations=list(unique.values()), issues=issues)

    async def batch(
        self,
        identifiers: list[str],
        format: CitationFormat = "bibtex",
        providers: list[str] | None = None,
        progress: Progress | None = None,
    ) -> BatchResult:
        if not 1 <= len(identifiers) <= 20:
            raise ValueError("Provide 1–20 identifiers per batch.")
        gate = asyncio.Semaphore(3)
        finished = 0

        async def item(identifier: str) -> BatchItem:
            nonlocal finished
            async with gate:
                try:
                    result = BatchItem(
                        identifier=identifier,
                        citation=await self.citation(identifier, format, providers),
                    )
                except (ValueError, ProviderError) as exc:
                    result = BatchItem(identifier=identifier, error=str(exc))
                finished += 1
                if progress:
                    await progress(finished, len(identifiers))
                return result

        items = await asyncio.gather(*(item(identifier) for identifier in identifiers))
        completed = sum(i.citation is not None for i in items)
        return BatchResult(items=items, completed=completed, failed=len(items) - completed)
