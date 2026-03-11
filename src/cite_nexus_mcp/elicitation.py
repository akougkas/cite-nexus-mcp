"""
MCP Elicitation helpers for CitePaper - offload text processing to the client LLM.
Provides OpenAI-compatible API fallback when MCP elicitation is unavailable.
"""
import os
import json
import asyncio
import requests
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

async def _call_openai(messages: list, schema: dict) -> dict:
    """Call an OpenAI-compatible API to act as a fallback for MCP elicitation."""
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # We append schema instruction to ensure the model returns what we expect
    messages.append({
        "role": "user",
        "content": f"Please provide the output as a JSON object adhering exactly to this JSON schema:\n{json.dumps(schema, indent=2)}\n\nOnly output the JSON object."
    })
    
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"}
    }
    
    def _post():
        response = requests.post(f"{api_base.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
        
    data = await asyncio.to_thread(_post)
    
    content = data["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from OpenAI fallback: {content}")
        return {}


async def elicit_title_extraction(text: str, client=None) -> str:
    """
    Extract paper title from any format using LLM.

    Args:
        text: Input text that might be a DOI, URL, ArXiv ID, citation, or title
        client: MCP client with elicitation capability

    Returns:
        Extracted paper title
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
        if os.getenv("OPENAI_API_KEY"):
            try:
                res = await _call_openai(
                    [
                        {"role": "system", "content": "You are a helpful assistant that extracts academic paper titles."},
                        {"role": "user", "content": f"Extract the academic paper title from this text. It might be a DOI, URL, ArXiv ID, citation, or the title itself: {text}"}
                    ],
                    schema
                )
                if "title" in res:
                    return res["title"]
            except Exception as e:
                logger.error(f"OpenAI fallback failed for title extraction: {e}")
        
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

    Args:
        metadata: Paper metadata from Google Scholar
        client: MCP client with elicitation capability

    Returns:
        Complete BibTeX entry
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
        if os.getenv("OPENAI_API_KEY"):
            try:
                res = await _call_openai(
                    [
                        {"role": "system", "content": "You are a helpful assistant that generates BibTeX citations."},
                        {"role": "user", "content": f"Generate a complete BibTeX entry from this Google Scholar metadata. Use author surname + year + first word of title for the citation key.\n\nMetadata:\n{json.dumps(metadata, indent=2)}"}
                    ],
                    schema
                )
                if "bibtex" in res:
                    return res["bibtex"]
            except Exception as e:
                logger.error(f"OpenAI fallback failed for bibtex generation: {e}")
                
        # Basic fallback for development
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
    
    Args:
        bibtex: Original BibTeX entry
        template: Template instructions or name
        client: MCP client with elicitation capability
        
    Returns:
        Enhanced/Formatted BibTeX entry
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

    message = f"Apply this formatting template/rules '{template}' to the following BibTeX entry. Only modify the formatting according to the template, preserve the data."

    if not client:
        if os.getenv("OPENAI_API_KEY"):
            try:
                res = await _call_openai(
                    [
                        {"role": "system", "content": "You are an expert at manipulating academic citations and BibTeX formatting."},
                        {"role": "user", "content": f"{message}\n\nBibTeX:\n{bibtex}"}
                    ],
                    schema
                )
                if "enhanced_bibtex" in res:
                    return res["enhanced_bibtex"]
            except Exception as e:
                logger.error(f"OpenAI fallback failed for template application: {e}")
        
        # Basic fallback is to return original
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
    # Clean first word for citation key
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
