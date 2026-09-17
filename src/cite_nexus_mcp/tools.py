"""Compatibility helpers for 0.1 Python callers. New integrations use ResearchService."""

from mcp.types import TextContent

from .citations import enhance
from .service import ResearchService


async def find_scholar_id(query: str, elicitation_client=None) -> TextContent:
    service = ResearchService()
    try:
        result = await service.search(query, ["serpapi"], limit=5)
        if not result.papers:
            return TextContent(type="text", text="No Scholar candidates found.")
        paper = result.papers[0]
        scholar_id = paper.identifiers.get("scholar")
        if not scholar_id:
            return TextContent(type="text", text="No Scholar cluster ID supplied by the source.")
        return TextContent(
            type="text",
            text=f"Found Google Scholar ID: {scholar_id}\nTitle: {paper.title}\nCandidate only; verify identity before citing.",
        )
    finally:
        await service.close()


async def get_citation(scholar_id: str, elicitation_client=None) -> TextContent:
    service = ResearchService()
    try:
        result = await service.citation(f"scholar:{scholar_id}")
        return TextContent(type="text", text=result.citation)
    finally:
        await service.close()


async def enhance_citation(
    bibtex: str, template: str = "default", elicitation_client=None
) -> TextContent:
    return TextContent(type="text", text=enhance(bibtex, template).bibtex)


async def paper_metrics(scholar_id: str) -> TextContent:
    service = ResearchService()
    try:
        result = await service.metrics(f"scholar:{scholar_id}")
        return TextContent(type="text", text=result.model_dump_json())
    finally:
        await service.close()
