"""Explicit live smoke check. No .env loading, API keys, paid providers or LLM calls."""

import asyncio
import json
from functools import partial

from cite_nexus_mcp.config import Settings
from cite_nexus_mcp.models import ProviderIssue
from cite_nexus_mcp.service import ResearchService


async def main() -> None:
    service = ResearchService(Settings(timeout=10, operation_timeout=15, retries=0))
    try:
        for name in ("crossref", "datacite", "europe_pmc", "arxiv", "semantic_scholar"):
            provider = service.providers[name]
            outcome = await service.attempt(
                provider, partial(provider.search, "deep learning", 2, 0)
            )
            if isinstance(outcome, ProviderIssue):
                print(json.dumps(outcome.model_dump()))
            else:
                print(
                    json.dumps(
                        {
                            "provider": name,
                            "papers": [{"id": p.id, "title": p.title} for p in outcome.papers],
                            "next_offset": outcome.next_offset,
                        }
                    )
                )
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
