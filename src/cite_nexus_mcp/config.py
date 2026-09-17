"""Explicit configuration; importing this package never reads .env or calls a service."""

import os

from pydantic import BaseModel, Field, SecretStr


class Settings(BaseModel):
    contact_email: str | None = None
    openalex_api_key: SecretStr | None = None
    semantic_scholar_api_key: SecretStr | None = None
    serpapi_api_key: SecretStr | None = None
    scopus_api_key: SecretStr | None = None
    scopus_insttoken: SecretStr | None = None
    wos_api_key: SecretStr | None = None
    unpaywall_email: str | None = None
    default_providers: tuple[str, ...] = ("crossref", "datacite", "europe_pmc")
    timeout: float = Field(default=12, ge=1, le=120)
    operation_timeout: float = Field(default=40, ge=1, le=300)
    retries: int = Field(default=1, ge=0, le=3)
    concurrency: int = Field(default=6, ge=1, le=20)
    cache_ttl: float = Field(default=300, ge=0, le=86400)
    cache_size: int = Field(default=256, ge=0, le=4096)

    @classmethod
    def from_env(cls) -> "Settings":
        names = {
            "contact_email": "CITE_NEXUS_CONTACT_EMAIL",
            "openalex_api_key": "OPENALEX_API_KEY",
            "semantic_scholar_api_key": "SEMANTIC_SCHOLAR_API_KEY",
            "serpapi_api_key": "SERPAPI_API_KEY",
            "scopus_api_key": "SCOPUS_API_KEY",
            "scopus_insttoken": "SCOPUS_INSTTOKEN",
            "wos_api_key": "WOS_API_KEY",
            "unpaywall_email": "UNPAYWALL_EMAIL",
            "timeout": "CITE_NEXUS_TIMEOUT",
            "operation_timeout": "CITE_NEXUS_OPERATION_TIMEOUT",
            "retries": "CITE_NEXUS_RETRIES",
            "concurrency": "CITE_NEXUS_CONCURRENCY",
            "cache_ttl": "CITE_NEXUS_CACHE_TTL",
            "cache_size": "CITE_NEXUS_CACHE_SIZE",
        }
        values = {field: os.environ[key] for field, key in names.items() if os.environ.get(key)}
        if "serpapi_api_key" not in values:
            if alias := os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_KEY"):
                values["serpapi_api_key"] = alias
        providers = os.getenv("CITE_NEXUS_DEFAULT_PROVIDERS")
        if providers:
            values["default_providers"] = tuple(  # type: ignore[assignment]
                dict.fromkeys(p.strip() for p in providers.split(",") if p.strip())
            )
        return cls.model_validate(values)


def secret(value: SecretStr | None) -> str | None:
    return value.get_secret_value() if value else None
