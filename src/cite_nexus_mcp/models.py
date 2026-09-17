"""Provider-independent records. Missing data stays missing."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def now() -> str:
    return datetime.now(UTC).isoformat()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Author(Model):
    name: str
    given: str | None = None
    family: str | None = None
    orcid: str | None = None


class Source(Model):
    provider: str
    record_id: str
    url: str
    retrieved_at: str = Field(default_factory=now)


class Metric(Model):
    provider: str
    count: int = Field(ge=0)
    observed_at: str = Field(default_factory=now)
    scope: str = "provider citation index"


class AccessLocation(Model):
    url: str
    provider: str
    is_open: bool | None = None
    version: str | None = None
    license: str | None = None


class Paper(Model):
    id: str
    title: str
    identifiers: dict[str, str] = Field(default_factory=dict)
    authors: list[Author] = Field(default_factory=list)
    authors_complete: bool = True
    year: int | None = None
    publication_date: str | None = None
    venue: str | None = None
    publisher: str | None = None
    type: str = "other"
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    abstract: str | None = None
    url: str | None = None
    is_retracted: bool | None = None
    access: list[AccessLocation] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    field_sources: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ProviderIssue(Model):
    provider: str
    code: str
    message: str
    retry_after: float | None = None


class SearchResult(Model):
    query: str
    papers: list[Paper]
    providers: list[str]
    issues: list[ProviderIssue] = Field(default_factory=list)
    returned: int
    next_offsets: dict[str, int] = Field(default_factory=dict)
    next_cursors: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class Resolution(Model):
    identifier: str
    paper: Paper
    issues: list[ProviderIssue] = Field(default_factory=list)


class CitationResult(Model):
    format: Literal["bibtex", "ris", "csl-json"]
    citation: str
    paper: Paper
    warnings: list[str] = Field(default_factory=list)


class VerificationResult(Model):
    status: Literal["verified", "mismatch", "ambiguous", "not_found", "unavailable"]
    identifier: str | None = None
    paper: Paper | None = None
    candidates: list[Paper] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    issues: list[ProviderIssue] = Field(default_factory=list)
    explanation: str


class ProviderInfo(Model):
    id: str
    name: str
    access: str
    description: str
    available: bool
    default: bool
    required_env: list[str]
    capabilities: list[str]
    documentation: str


class ProvidersResult(Model):
    providers: list[ProviderInfo]
    policy: str


class GraphResult(Model):
    identifier: str
    direction: Literal["citations", "references"]
    provider: str
    papers: list[Paper]
    returned: int
    next_offset: int | None = None
    warnings: list[str] = Field(default_factory=list)


class MetricsResult(Model):
    paper: Paper
    metrics: list[Metric]
    issues: list[ProviderIssue] = Field(default_factory=list)
    interpretation: str = (
        "Counts reflect each provider's coverage and observation time. "
        "Do not sum counts across providers or use them alone to assess research quality."
    )


class AccessResult(Model):
    paper: Paper
    locations: list[AccessLocation]
    issues: list[ProviderIssue] = Field(default_factory=list)


class BatchItem(Model):
    identifier: str
    citation: CitationResult | None = None
    error: str | None = None


class BatchResult(Model):
    items: list[BatchItem]
    completed: int
    failed: int


class EnhancementResult(Model):
    bibtex: str
    warnings: list[str]
