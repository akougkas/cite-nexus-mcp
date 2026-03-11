"""
MCP Elicitation helpers for CitePaper - offload text processing to the client LLM.
Provides dynamic LLM factory fallbacks when MCP elicitation is unavailable.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

from .llm_factory import LLMFactory

logger = logging.getLogger(__name__)

async def elicit_title_extraction(text: str, client=None) -> str:
    """
    Extract paper title from any format using LLM.
    """
    schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The extracted paper title"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence in extraction (0-1)"
            }
        },
        "required": ["title"]
    }

    if not client:
        provider = LLMFactory.get_provider()
        if provider:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that extracts academic paper titles."},
                {"role": "user", "content": f"Extract the academic paper title from this text. It might be a DOI, URL, ArXiv ID, citation, or the title itself: {text}"}
            ]
            try:
                res = await provider.generate_json(messages, schema)
                if res and "title" in res:
                    return res["title"]
            except Exception as e:
                logger.error(f"Fallback provider failed for title extraction: {e}")
        
        # Fallback for simple cases during development
        if text.startswith("10."):  # DOI
            return text  # Let Scholar API handle it
        return text.strip()

    response = await client.elicitation_create({
        "message": "Extract the academic paper title from this text. It might be a DOI, URL, ArXiv ID, citation, or the title itself.",
        "context": text,
        "requestedSchema": schema
    })
    return response.get("title", text.strip())


async def elicit_bibtex_generation(metadata: Dict[str, Any], client=None) -> str:
    """
    Generate BibTeX from paper metadata using LLM.
    """
    schema = {
        "type": "object",
        "properties": {
            "bibtex": {
                "type": "string",
                "description": "Complete BibTeX entry"
            },
            "entry_type": {
                "type": "string",
                "enum": ["article", "inproceedings", "book", "misc"],
                "description": "BibTeX entry type"
            }
        },
        "required": ["bibtex", "entry_type"]
    }

    if not client:
        provider = LLMFactory.get_provider()
        if provider:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that generates BibTeX citations."},
                {"role": "user", "content": f"Generate a complete BibTeX entry from this Google Scholar metadata. Use author surname + year + first word of title for the citation key.\n\nMetadata:\n{json.dumps(metadata, indent=2)}"}
            ]
            try:
                res = await provider.generate_json(messages, schema)
                if res and "bibtex" in res:
                    return res["bibtex"]
            except Exception as e:
                logger.error(f"Fallback provider failed for bibtex generation: {e}")
                
        return generate_basic_bibtex(metadata)

    response = await client.elicitation_create({
        "message": "Generate a complete BibTeX entry from this Google Scholar metadata. Use author surname + year + first word of title for the citation key.",
        "context": json.dumps(metadata, indent=2),
        "requestedSchema": schema
    })
    return response.get("bibtex", generate_basic_bibtex(metadata))


async def elicit_template_application(bibtex: str, template: str, client=None) -> str:
    """
    Apply a formatting template to a BibTeX entry using LLM.
    """
    schema = {
        "type": "object",
        "properties": {
            "enhanced_bibtex": {
                "type": "string",
                "description": "The enhanced BibTeX entry with the template applied"
            }
        },
        "required": ["enhanced_bibtex"]
    }

    message = (
        f"Analyze the following BibTeX entry. Your task is to:\n"
        f"1. Apply the following formatting rules or template: '{template}' (if 'default', apply standard academic best practices).\n"
        f"2. Intelligently enhance the metadata: infer and add relevant 'keywords' based on the title/venue, ensure proper capitalization of titles (protecting acronyms with curly braces), standardize field names, and add any other implicit metadata that improves the citation.\n"
        f"3. Return the fully enhanced, valid BibTeX entry."
    )

    if not client:
        provider = LLMFactory.get_provider()
        if provider:
            messages = [
                {"role": "system", "content": "You are an expert academic librarian and BibTeX curator. You intuitively enhance and fix citations."},
                {"role": "user", "content": f"{message}\n\nBibTeX:\n{bibtex}"}
            ]
            try:
                res = await provider.generate_json(messages, schema)
                if res and "enhanced_bibtex" in res:
                    return res["enhanced_bibtex"]
            except Exception as e:
                logger.error(f"Fallback provider failed for template application: {e}")
        
        return bibtex

    response = await client.elicitation_create({
        "message": message,
        "context": bibtex,
        "requestedSchema": schema
    })
    return response.get("enhanced_bibtex", bibtex)


def generate_basic_bibtex(metadata: Dict[str, Any]) -> str:
    """
    Generate basic BibTeX without elicitation (fallback).
    """
    authors = metadata.get("authors", [])
    if authors:
        first_author = authors[0].split()[-1] if isinstance(authors[0], str) else "Unknown"
    else:
        first_author = "Unknown"

    year = metadata.get("year", "")
    title = metadata.get("title", "Unknown Title")
    import re
    first_word = re.sub(r'[^a-zA-Z0-9]', '', title.split()[0]) if title else "Unknown"

    citation_key = f"{first_author}{year}{first_word}".replace(" ", "")

    venue = metadata.get("venue", "").lower()
    entry_type = "misc"
    if "conference" in venue or "proceedings" in venue or "ieee" in venue or "acm" in venue:
        entry_type = "inproceedings"
    elif "journal" in venue or "arxiv" in venue:
        entry_type = "article"

    bibtex = f"@{entry_type}{{{citation_key},\n"
    bibtex += f'  title = {{{title}}},\n'
    if authors:
        bibtex += f'  author = {{' + ' and '.join(authors) + '},\n'
    if year:
        bibtex += f'  year = {{{year}}},\n'
    
    if venue:
        if entry_type == "inproceedings":
            bibtex += f'  booktitle = {{{metadata.get("venue", "")}}},\n'
        elif entry_type == "article":
            bibtex += f'  journal = {{{metadata.get("venue", "")}}},\n'
    
    if metadata.get("doi"):
        bibtex += f'  doi = {{{metadata["doi"]}}},\n'
    if metadata.get("url"):
        bibtex += f'  url = {{{metadata["url"]}}},\n'
        
    bibtex += '}'

    return bibtex