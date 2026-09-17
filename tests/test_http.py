import asyncio

import httpx2 as httpx
import pytest

from cite_nexus_mcp.config import Settings
from cite_nexus_mcp.http import HTTP, ProviderError


async def test_cache_is_bounded_and_partitions_credentials():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"value": len(calls)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = HTTP(Settings(cache_size=1), client)
        first = await http.json("test", "https://api.example.org/works", headers={"key": "one"})
        assert (
            await http.json("test", "https://api.example.org/works", headers={"key": "one"})
            == first
        )
        await http.json("test", "https://api.example.org/works", headers={"key": "two"})
        await http.json("test", "https://api.example.org/works", headers={"key": "one"})
        assert len(calls) == 3
        assert len(http._cache) == 1


async def test_retry_after_does_not_block_for_long_cooldowns():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                429, headers={"Retry-After": "120"}, text="private upstream error"
            )
        )
    ) as client:
        http = HTTP(Settings(), client)
        with pytest.raises(ProviderError) as caught:
            await http.json("test", "https://api.example.org/?api_key=secret")
    assert caught.value.issue.code == "rate_limited"
    assert caught.value.issue.retry_after == 120
    assert "secret" not in str(caught.value)
    assert "private" not in str(caught.value)


async def test_transient_error_retries_once():
    count = 0

    def handler(_):
        nonlocal count
        count += 1
        return (
            httpx.Response(503, headers={"Retry-After": "0"})
            if count == 1
            else httpx.Response(200, json={"ok": True})
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = HTTP(Settings(retries=1), client)
        assert await http.json("test", "https://api.example.org/", interval=0) == {"ok": True}
    assert count == 2


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "access_denied"),
        (403, "access_denied"),
        (404, "not_found"),
        (400, "http_error"),
        (302, "http_error"),
    ],
)
async def test_http_errors_do_not_leak_response_or_key(status, code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status, text="secret body"))
    ) as client:
        http = HTTP(Settings(retries=0), client)
        with pytest.raises(ProviderError) as caught:
            await http.get("test", "https://api.example.org/?key=secret-key")
    assert caught.value.issue.code == code
    assert "secret" not in str(caught.value)


async def test_timeout_is_sanitized():
    def handler(request):
        raise httpx.ReadTimeout("secret URL", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = HTTP(Settings(retries=0), client)
        with pytest.raises(ProviderError, match="could not be reached"):
            await http.json("test", "https://api.example.org/")


async def test_invalid_json_and_oversize_are_rejected():
    for data, code in [(b"not json", "invalid_response"), (b"x" * 8_000_001, "response_too_large")]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _, data=data: httpx.Response(200, content=data))
        ) as client:
            with pytest.raises(ProviderError) as caught:
                await HTTP(Settings(), client).json("test", "https://api.example.org/")
        assert caught.value.issue.code == code


async def test_cancellation_is_not_swallowed():
    async def handler(request):
        raise asyncio.CancelledError

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(asyncio.CancelledError):
            await HTTP(Settings(), client).json("test", "https://api.example.org/")


async def test_cached_response_keeps_original_observation_time():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True}))
    ) as client:
        http = HTTP(Settings(), client)
        await http.json("test", "https://api.example.org/")
        original = http.retrieved_at["test"]
        http.retrieved_at["test"] = "newer unrelated request"
        await http.json("test", "https://api.example.org/")
        assert http.retrieved_at["test"] == original


async def test_invalid_json_is_not_cached():
    calls = 0

    def handler(_):
        nonlocal calls
        calls += 1
        return (
            httpx.Response(200, text="bad json")
            if calls == 1
            else httpx.Response(200, json={"ok": True})
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = HTTP(Settings(), client)
        with pytest.raises(ProviderError):
            await http.json("test", "https://api.example.org/")
        assert await http.json("test", "https://api.example.org/") == {"ok": True}


async def test_owned_client_offers_post_handshake_auth_like_the_stdlib_https_client(monkeypatch):
    # arXiv's CDN answers HTTP 406 to TLS clients that offer ALPN without post-handshake auth,
    # which is httpcore's default; Python's http.client enables it and is accepted.
    created = {}

    class Recorder(httpx.AsyncClient):
        def __init__(self, **kwargs):
            created.update(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", Recorder)
    http = HTTP(Settings())
    try:
        assert created["verify"].post_handshake_auth is True
        assert created["verify"].verify_mode.name == "CERT_REQUIRED"
        assert created["verify"].check_hostname is True
    finally:
        await http.close()
