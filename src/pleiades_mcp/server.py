"""
CitePaper MCP Server - Simplified Google Scholar-based citation tools.
"""
import logging
import os
from dotenv import load_dotenv
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Load environment variables from .env file
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Import our simplified tools
from .tools import find_scholar_id, get_citation, enhance_citation, paper_metrics

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server with elicitation capability
server = Server("cite-paper")

# Store elicitation client when available
elicitation_client = None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List our 4 focused tools for citation management.
    """
    return [
        types.Tool(
            name="find-scholar-id",
            description="Universal paper discovery tool that converts any input (title, DOI, ArXiv ID, URL, citation text) into a Google Scholar cluster ID. Uses MCP Elicitation to intelligently extract paper titles from any format, then performs a single SerpAPI search to find the unique Scholar ID. This ID serves as the universal key for all other tools. Returns the cluster ID that uniquely identifies the paper in Google Scholar's database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Paper identifier: title, DOI (10.xxx/xxx), ArXiv ID (1234.5678), URL, or citation text"
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get-citation",
            description="BibTeX generation tool that creates complete, properly formatted citations from a Google Scholar cluster ID. Performs a direct API lookup to retrieve all available metadata (title, authors, year, venue, abstract, DOI, citations) and uses MCP Elicitation to generate a professional BibTeX entry with smart citation keys (author+year+keyword format). Returns publication-ready BibTeX that includes all available fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_id": {
                        "type": "string",
                        "description": "Google Scholar cluster ID (e.g., 'TQgYirikUcIC')"
                    },
                },
                "required": ["scholar_id"],
            },
        ),
        types.Tool(
            name="enhance-citation",
            description="Citation enhancement tool that applies custom templates and formatting rules to existing BibTeX entries. Uses MCP Elicitation to transform basic citations into institution-specific formats, add custom fields (awards, rankings, notes), fix formatting issues, and ensure consistency with your bibliography style. Ideal for converting generic BibTeX into your preferred academic format for thesis, papers, or applications.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bibtex": {
                        "type": "string",
                        "description": "Existing BibTeX entry to enhance"
                    },
                    "template": {
                        "type": "string",
                        "description": "Template name or custom formatting rules (default: 'default')",
                        "default": "default"
                    },
                },
                "required": ["bibtex"],
            },
        ),
        types.Tool(
            name="paper-metrics",
            description="Comprehensive paper analytics tool that extracts impact metrics and scholarly influence data. For a given Scholar cluster ID, retrieves citation count, citation velocity (recent vs all-time), h-index of authors, venue impact factor, field-relative metrics, awards and recognition, top citing papers, and citation network analysis. Returns structured metrics ideal for research evaluation, grant applications, and academic assessment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scholar_id": {
                        "type": "string",
                        "description": "Google Scholar cluster ID for impact analysis"
                    },
                },
                "required": ["scholar_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution with our simplified architecture.
    """
    if not arguments:
        return [types.TextContent(
            type="text",
            text="Error: No arguments provided"
        )]

    try:
        if name == "find-scholar-id":
            result = await find_scholar_id(arguments.get("query", ""), elicitation_client)
            return [result]

        elif name == "get-citation":
            result = await get_citation(arguments.get("scholar_id", ""), elicitation_client)
            return [result]

        elif name == "enhance-citation":
            result = await enhance_citation(
                arguments.get("bibtex", ""),
                arguments.get("template", "default"),
                elicitation_client
            )
            return [result]

        elif name == "paper-metrics":
            result = await paper_metrics(arguments.get("scholar_id", ""))
            return [result]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    # Try to load .env explicitly
    try:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        if key == 'SERP_API_KEY':
                            os.environ['SERP_API_KEY'] = value
                            logger.info(f"Loaded SERP_API_KEY from .env file")
                            break
    except Exception as e:
        logger.warning(f"Could not load .env file: {e}")

    # Check for API key but continue anyway
    if not os.getenv("SERP_API_KEY"):
        logger.warning("SERP_API_KEY environment variable not set")
        logger.warning("Tools will fail without a valid SerpAPI key")
        logger.info("Starting server anyway - set SERP_API_KEY in .env file or environment")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="cite-paper",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run():
    """Entry point for the server."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run()