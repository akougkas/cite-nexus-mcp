"""Bounded asynchronous HTTP, per-provider pacing, retries and an in-memory cache."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx2 as httpx

from .config import Settings
from .models import ProviderIssue, now


class ProviderError(Exception):
    def __init__(self, provider: str, code: str, message: str, retry_after: float | None = None):
        super().__init__(f"{provider}: {message}")
        self.issue = ProviderIssue(
            provider=provider, code=code, message=message, retry_after=retry_after
        )


class HTTP:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._owned = client is None
        self.client = client or httpx.AsyncClient(
            timeout=settings.timeout,
            follow_redirects=False,
            headers={"User-Agent": "CiteNexus/0.2 (+https://github.com/akougkas/cite-nexus-mcp)"},
            limits=httpx.Limits(max_connections=settings.concurrency, max_keepalive_connections=10),
        )
        self._semaphore = asyncio.Semaphore(settings.concurrency)
        self._locks: dict[str, asyncio.Lock] = {}
        self._next: dict[str, float] = {}
        self._cache: OrderedDict[str, tuple[float, bytes, str]] = OrderedDict()
        self.retrieved_at: dict[str, str] = {}

    async def close(self) -> None:
        if self._owned:
            await self.client.aclose()

    async def _pace(self, provider: str, interval: float) -> None:
        async with self._locks.setdefault(provider, asyncio.Lock()):
            delay = self._next.get(provider, 0) - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next[provider] = time.monotonic() + interval

    @staticmethod
    def _retry_delay(value: str | None, attempt: int) -> float:
        if value:
            try:
                return max(0, float(value))
            except ValueError:
                try:
                    return max(
                        0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
        return float(2**attempt)

    async def get(
        self,
        provider: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        interval: float = 0.1,
    ) -> bytes:
        key = hashlib.sha256(
            json.dumps([url, params, headers], sort_keys=True).encode()
        ).hexdigest()
        cached = self._cache.get(key)
        if cached and cached[0] > time.monotonic():
            self._cache.move_to_end(key)
            self.retrieved_at[provider] = cached[2]
            return cached[1]
        if cached:
            del self._cache[key]
        for attempt in range(self.settings.retries + 1):
            await self._pace(provider, interval)
            try:
                async with (
                    self._semaphore,
                    self.client.stream(
                        "GET", url, params=params, headers=headers, timeout=self.settings.timeout
                    ) as response,
                ):
                    status = response.status_code
                    if status == 429 or 500 <= status < 600:
                        delay = self._retry_delay(response.headers.get("Retry-After"), attempt)
                        # Long provider cooldowns should not occupy an MCP request.
                        if attempt < self.settings.retries and delay <= 5:
                            self._next[provider] = max(
                                self._next.get(provider, 0), time.monotonic() + delay
                            )
                            continue
                        raise ProviderError(
                            provider,
                            "rate_limited" if status == 429 else "upstream_error",
                            f"Provider returned HTTP {status}; try again later.",
                            delay,
                        )
                    if status == 404:
                        raise ProviderError(provider, "not_found", "Record was not found.")
                    if status in {401, 403}:
                        raise ProviderError(
                            provider,
                            "access_denied",
                            "Check the API key, quota, and institutional entitlement.",
                        )
                    if status >= 300:
                        raise ProviderError(
                            provider, "http_error", f"Provider returned HTTP {status}."
                        )
                    chunks = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 8_000_000:
                            raise ProviderError(
                                provider,
                                "response_too_large",
                                "Response exceeded 8 MB; reduce the page size.",
                            )
                        chunks.append(chunk)
                    data = b"".join(chunks)
            except httpx.TransportError:
                if attempt < self.settings.retries:
                    continue
                raise ProviderError(
                    provider,
                    "network_error",
                    "Request timed out or the provider could not be reached.",
                ) from None
            observed = now()
            self.retrieved_at[provider] = observed
            if self.settings.cache_size and self.settings.cache_ttl:
                self._cache[key] = (time.monotonic() + self.settings.cache_ttl, data, observed)
                while len(self._cache) > self.settings.cache_size:
                    self._cache.popitem(last=False)
            return data
        raise AssertionError("unreachable")

    async def json(self, provider: str, url: str, **kwargs: Any) -> dict[str, Any]:
        data = await self.get(provider, url, **kwargs)
        try:
            result = json.loads(data)
            if not isinstance(result, dict):
                raise ValueError
            return result
        except (ValueError, UnicodeDecodeError):
            key = hashlib.sha256(
                json.dumps(
                    [url, kwargs.get("params"), kwargs.get("headers")], sort_keys=True
                ).encode()
            ).hexdigest()
            self._cache.pop(key, None)
            raise ProviderError(
                provider, "invalid_response", "Provider returned invalid JSON."
            ) from None
