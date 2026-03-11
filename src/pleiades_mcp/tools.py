"""
Four focused tools for citation management using Google Scholar IDs.
"""
import json
import logging
from typing import Dict, Any, Optional
from mcp.types import TextContent

from .scholar_api import ScholarAPI
from .elicitation import elicit_title_extraction, elicit_bibtex_generation, elicit_template_application

logger = logging.getLogger(__name__)


async def find_scholar_id(query: str, elicitation_client=None) -> TextContent:
    """
    Tool 1: Convert any input to Google Scholar ID.

    Args:
        query: Title, DOI, ArXiv ID, URL, or citation text
        elicitation_client: Optional MCP client with elicitation capability

    Returns:
        Google Scholar cluster ID
    """
    try:
        scholar = ScholarAPI()

        # Use elicitation to extract title if we have complex input
        title = await elicit_title_extraction(query, elicitation_client)

        # Search for the paper
        result = scholar.find_paper(title)

        if result and "cluster_id" in result:
            response = {
                "scholar_id": result["cluster_id"],
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "year": extract_year(result),
                "authors": extract_authors(result)
            }
            return TextContent(
                type="text",
                text=f"Found Google Scholar ID: {result['cluster_id']}\n\n"
                     f"Title: {response['title']}\n"
                     f"Year: {response['year']}\n"
                     f"Authors: {', '.join(response['authors'][:3])}"
            )
        else:
            return TextContent(
                type="text",
                text="Could not find paper in Google Scholar. Please try a more specific query."
            )

    except Exception as e:
        logger.error(f"Error finding scholar ID: {e}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )


async def get_citation(scholar_id: str, elicitation_client=None) -> TextContent:
    """
    Tool 2: Generate complete BibTeX from Scholar ID.

    Args:
        scholar_id: Google Scholar cluster ID
        elicitation_client: Optional MCP client with elicitation capability

    Returns:
        Complete BibTeX entry
    """
    try:
        scholar = ScholarAPI()

        # Get complete metadata using cluster ID
        paper_data = scholar.get_paper_by_id(scholar_id)

        if not paper_data:
            return TextContent(
                type="text",
                text=f"Could not find paper with Scholar ID: {scholar_id}"
            )

        # Extract metadata
        metadata = {
            "title": extract_title(paper_data),
            "authors": extract_authors_from_cluster(paper_data),
            "year": extract_year_from_cluster(paper_data),
            "venue": extract_venue(paper_data),
            "doi": extract_doi(paper_data),
            "url": extract_url(paper_data),
            "abstract": extract_abstract(paper_data)
        }

        # Generate BibTeX using elicitation or fallback
        bibtex = await elicit_bibtex_generation(metadata, elicitation_client)

        return TextContent(
            type="text",
            text=bibtex
        )

    except Exception as e:
        logger.error(f"Error generating citation: {e}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )


async def enhance_citation(bibtex: str, template: str = "default", elicitation_client=None) -> TextContent:
    """
    Tool 3: Apply custom template to BibTeX.

    Args:
        bibtex: Existing BibTeX entry
        template: Template name or custom rules
        elicitation_client: Optional MCP client with elicitation capability

    Returns:
        Enhanced BibTeX with custom formatting
    """
    try:
        enhanced_bibtex = await elicit_template_application(bibtex, template, elicitation_client)

        return TextContent(
            type="text",
            text=f"Enhanced citation (template: {template}):\n\n{enhanced_bibtex}"
        )

    except Exception as e:
        logger.error(f"Error enhancing citation: {e}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )


async def paper_metrics(scholar_id: str) -> TextContent:
    """
    Tool 4: Extract paper analytics and impact metrics.

    Args:
        scholar_id: Google Scholar cluster ID

    Returns:
        Structured metrics and impact analysis
    """
    try:
        scholar = ScholarAPI()

        # Get paper metadata
        paper_data = scholar.get_paper_by_id(scholar_id)

        # Get citations
        citations = scholar.get_citations(scholar_id, limit=10)

        # Extract metrics
        metrics = {
            "paper_title": extract_title(paper_data),
            "citation_count": len(citations),
            "year": extract_year_from_cluster(paper_data),
            "top_citing_papers": [
                {
                    "title": c.get("title", ""),
                    "year": extract_year(c),
                    "authors": extract_authors(c)[:3]
                }
                for c in citations[:5]
            ]
        }

        # Format metrics report
        report = f"Paper Metrics for Scholar ID: {scholar_id}\n"
        report += f"{'=' * 50}\n\n"
        report += f"Title: {metrics['paper_title']}\n"
        report += f"Year: {metrics['year']}\n"
        report += f"Total Citations: {metrics['citation_count']}\n\n"

        if metrics['top_citing_papers']:
            report += "Top Citing Papers:\n"
            for i, paper in enumerate(metrics['top_citing_papers'], 1):
                report += f"{i}. {paper['title']} ({paper['year']})\n"

        return TextContent(
            type="text",
            text=report
        )

    except Exception as e:
        logger.error(f"Error getting paper metrics: {e}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )


# Helper functions for data extraction
def extract_year(result: Dict) -> str:
    """Extract year from search result."""
    if "publication_info" in result:
        info = result["publication_info"]
        if "summary" in info:
            # Look for all 4-digit years in summary and take the last one
            import re
            matches = re.findall(r'\b(?:19|20)\d{2}\b', info["summary"])
            if matches:
                return matches[-1]
    return ""


def extract_year_from_cluster(data: Dict) -> str:
    """Extract year from cluster data."""
    # Check organic_results first
    if "organic_results" in data and data["organic_results"]:
        return extract_year(data["organic_results"][0])
    return extract_year(data)


def extract_authors(result: Dict) -> list:
    """Extract authors from search result."""
    if "publication_info" in result:
        info = result["publication_info"]
        if "authors" in info:
            return [a["name"] for a in info["authors"] if "name" in a]
    return []


def extract_authors_from_cluster(data: Dict) -> list:
    """Extract authors from cluster data."""
    if "organic_results" in data and data["organic_results"]:
        return extract_authors(data["organic_results"][0])
    return extract_authors(data)


def extract_title(data: Dict) -> str:
    """Extract title from paper data."""
    if "organic_results" in data and data["organic_results"]:
        return data["organic_results"][0].get("title", "")
    return data.get("title", "")


def extract_venue(data: Dict) -> str:
    """Extract venue/publication from paper data."""
    if "organic_results" in data and data["organic_results"]:
        result = data["organic_results"][0]
        if "publication_info" in result:
            return result["publication_info"].get("summary", "")
    return ""


def extract_doi(data: Dict) -> str:
    """Extract DOI if available."""
    # Would need to parse from links or description
    return ""


def extract_url(data: Dict) -> str:
    """Extract URL from paper data."""
    if "organic_results" in data and data["organic_results"]:
        return data["organic_results"][0].get("link", "")
    return data.get("link", "")


def extract_abstract(data: Dict) -> str:
    """Extract abstract/snippet from paper data."""
    if "organic_results" in data and data["organic_results"]:
        return data["organic_results"][0].get("snippet", "")
    return data.get("snippet", "")


def generate_simple_bibtex(metadata: Dict[str, Any]) -> str:
    """Generate simple BibTeX entry without elicitation."""
    authors = metadata.get("authors", [])
    if authors:
        first_author = authors[0].split()[-1] if authors else "Unknown"
    else:
        first_author = "Unknown"

    year = metadata.get("year", "")
    title = metadata.get("title", "Unknown Title")
    first_word = title.split()[0] if title else "Unknown"

    citation_key = f"{first_author}{year}{first_word}".replace(" ", "").replace(",", "")

    # Determine entry type based on venue
    venue = metadata.get("venue", "").lower()
    if "conference" in venue or "proceedings" in venue:
        entry_type = "inproceedings"
    elif "journal" in venue:
        entry_type = "article"
    else:
        entry_type = "misc"

    bibtex = f"@{entry_type}{{{citation_key},\n"
    bibtex += f'  title = {{{title}}},\n'

    if authors:
        bibtex += f'  author = {{' + ' and '.join(authors) + '},\n'

    if year:
        bibtex += f'  year = {{{year}}},\n'

    if venue:
        if entry_type == "inproceedings":
            bibtex += f'  booktitle = {{{venue}}},\n'
        elif entry_type == "article":
            bibtex += f'  journal = {{{venue}}},\n'

    if metadata.get("doi"):
        bibtex += f'  doi = {{{metadata["doi"]}}},\n'

    if metadata.get("url"):
        bibtex += f'  url = {{{metadata["url"]}}},\n'

    bibtex += '}'

    return bibtex