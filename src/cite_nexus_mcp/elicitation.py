"""Deprecated Python helpers; MCP elicitation is user input, not citation generation.

The MCP server does not import this module. Kept for existing 0.1 Python callers;
bibliographic output now uses the same deterministic renderer as the server.
"""

from typing import Any

from .citations import enhance, format_citation
from .identifiers import normalize_doi
from .models import Author, Paper


async def elicit_title_extraction(text: str, client=None) -> str:
    """Preserve the input query. Discovery and identifier resolution belong to providers."""
    return text.strip()


def generate_basic_bibtex(metadata: dict[str, Any]) -> str:
    doi = normalize_doi(metadata.get("doi"))
    authors = [Author(name=name) for name in metadata.get("authors", []) if isinstance(name, str)]
    year = str(metadata.get("year", ""))
    paper = Paper(
        id=f"doi:{doi}" if doi else "legacy:metadata",
        title=metadata.get("title", ""),
        identifiers={"doi": doi} if doi else {},
        authors=authors,
        year=int(year) if year.isdigit() else None,
        venue=metadata.get("venue") or None,
        url=metadata.get("url") or None,
    )
    return format_citation(paper).citation


async def elicit_bibtex_generation(metadata: dict[str, Any], client=None) -> str:
    return generate_basic_bibtex(metadata)


async def elicit_template_application(bibtex: str, template: str, client=None) -> str:
    return enhance(bibtex, template).bibtex
