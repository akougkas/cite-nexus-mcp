"""Small provider interface and shared normalization helpers."""

import html
import re
from dataclasses import dataclass
from typing import Any

from ..config import Settings
from ..http import HTTP, ProviderError
from ..identifiers import Identifier, normalize_doi
from ..models import Paper, ProviderInfo, Source, now


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", "", str(value)))
    return " ".join(text.split()) or None


def integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (ValueError, TypeError):
        return None


def first(value: list[Any] | None) -> Any:
    return value[0] if value else None


@dataclass
class Page:
    papers: list[Paper]
    next_offset: int | None = None
    next_cursor: str | None = None


class Provider:
    id = ""
    name = ""
    access = "free"
    description = ""
    documentation = ""
    required_env: tuple[str, ...] = ()
    credential: str | None = None
    kinds: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ("search", "resolve")
    max_limit = 50

    def __init__(self, http: HTTP, settings: Settings):
        self.http = http
        self.settings = settings

    @property
    def available(self) -> bool:
        return not self.credential or bool(getattr(self.settings, self.credential))

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id=self.id,
            name=self.name,
            access=self.access,
            description=self.description,
            available=self.available,
            default=self.id in self.settings.default_providers,
            required_env=list(self.required_env),
            capabilities=list(self.capabilities),
            documentation=self.documentation,
        )

    def require(self) -> None:
        if not self.available:
            raise ProviderError(
                self.id, "not_configured", "Set " + ", ".join(self.required_env) + "."
            )

    def paper(self, record_id: str, source_url: str, **fields: Any) -> Paper:
        identifiers = fields.pop("identifiers", {})
        if doi := normalize_doi(identifiers.get("doi")):
            identifiers["doi"] = doi
        else:
            identifiers.pop("doi", None)
        identifiers = {k: str(v) for k, v in identifiers.items() if v}
        if "arxiv" in identifiers:
            identifiers["arxiv"] = re.sub(r"v\d+$", "", identifiers["arxiv"], flags=re.I)
        if "pmcid" in identifiers:
            identifiers["pmcid"] = "PMC" + identifiers["pmcid"].upper().removeprefix("PMC")
        paper_id = next(
            (
                f"{kind}:{identifiers[kind]}"
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
                    "europe_pmc",
                )
                if kind in identifiers
            ),
            f"{self.id}:{record_id}",
        )
        if fields.get("type") in {"preprint", "posted-content"} and identifiers.get("arxiv"):
            paper_id = f"arxiv:{identifiers['arxiv']}"
        fields["title"] = clean(fields.get("title")) or "[Title unavailable]"
        if fields["title"] == "[Title unavailable]":
            fields.setdefault("warnings", []).append("The source did not supply a title.")
        observed = self.http.retrieved_at.get(self.id, now()) if self.http else now()
        for metric in fields.get("metrics", []):
            metric.observed_at = observed
        return Paper(
            id=paper_id,
            identifiers=identifiers,
            sources=[
                Source(provider=self.id, record_id=record_id, url=source_url, retrieved_at=observed)
            ],
            field_sources={
                **{k: [self.id] for k, v in fields.items() if v is not None and v != []},
                **{f"identifiers.{kind}": [self.id] for kind in identifiers},
            },
            **fields,
        )

    async def search(self, query: str, limit: int, offset: int) -> Page:
        raise NotImplementedError

    async def resolve(self, identifier: Identifier) -> Paper:
        raise ProviderError(
            self.id, "unsupported_identifier", f"Cannot resolve {identifier.kind} identifiers."
        )

    async def graph(self, identifier: Identifier, direction: str, limit: int, offset: int) -> Page:
        raise ProviderError(
            self.id, "unsupported_operation", f"Does not expose {direction} through CiteNexus."
        )
