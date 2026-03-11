# CitePaper MCP

A modern, fast [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that gives your AI assistant the ability to search academic papers, generate highly accurate BibTeX citations, format references, and pull impact metrics using Google Scholar.

Unlike standard citation generators that rely on complex regex parsing or multi-source fallbacks (arXiv, Crossref, etc.), **CitePaper MCP** uses Google Scholar Cluster IDs as the single source of truth and leverages LLM elicitation (via MCP or OpenAI-compatible API) to elegantly format and extract metadata.

It’s the perfect "citation engine" for your research workflows and AI-assisted drafting tools (like [WTF-P](https://github.com/akougkas/wtf-p)).

---

## ✨ Features

- **Google Scholar as the Universal Key:** Uses unique Google Scholar Cluster IDs to identify papers, avoiding the mess of conflicting DOIs, ArXiv IDs, or slight title mismatches.
- **LLM-Powered Formatting (Elicitation):** Offloads complex BibTeX generation, custom templating, and text extraction to the AI client itself via the MCP Elicitation API.
- **OpenAI API Fallback:** If your AI client (like Claude Code or Gemini CLI) doesn't natively support MCP Elicitation yet, the server automatically falls back to any OpenAI-compatible API (OpenAI, Ollama, vLLM) to perform the data formatting.
- **Modern Python Architecture:** Built on top of the official Python MCP SDK, packaged beautifully with `uv`.

## 🛠️ Tools Provided

1. **`find-scholar-id`**: Converts any input (Title, DOI, ArXiv ID, partial citation) into a universal Google Scholar Cluster ID.
2. **`get-citation`**: Generates a complete, highly-accurate BibTeX entry from a Scholar ID.
3. **`enhance-citation`**: Applies custom templates and formatting instructions to existing BibTeX entries (e.g., "Make authors first-initial only", "Add custom note").
4. **`paper-metrics`**: Extracts citation counts, h-index, and top citing papers for a given Scholar ID.

## 🚀 Quickstart with `uvx`

Because CitePaper MCP is published to PyPI (or your local structure) and built with `uv`, you can run it instantly using `uvx` without installing dependencies globally.

### Prerequisites

You need a [SerpAPI Key](https://serpapi.com/) to query Google Scholar.

```bash
export SERP_API_KEY="your-serpapi-key"
```

**(Optional) Fallback API Configuration:**
If your MCP client does not support elicitation (like Claude Code/Gemini CLI), provide an API key to handle formatting.

```bash
export OPENAI_API_KEY="sk-..."
# Optional: Use local/custom endpoints
# export OPENAI_API_BASE="http://localhost:11434/v1" 
# export OPENAI_MODEL="llama3"
```

### Running the Server

You can run the server directly using `uvx`:

```bash
uvx cite-paper-mcp
```

### Installing in Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cite-paper": {
      "command": "uvx",
      "args": [
        "cite-paper-mcp"
      ],
      "env": {
        "SERP_API_KEY": "your-serp-api-key",
        "OPENAI_API_KEY": "your-openai-api-key-if-needed"
      }
    }
  }
}
```

## 🏗️ Development & Manual Installation

To work on the codebase or run it locally from source:

1. Install `uv` if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Clone and install the dependencies:
   ```bash
   git clone https://github.com/akougkas/cite-paper-mcp.git
   cd cite-paper-mcp
   uv sync
   ```
3. Run the server:
   ```bash
   uv run cite-paper-mcp
   ```

## 🤝 Philosophy

This repository follows the "Engine in the Car" philosophy. `cite-paper-mcp` is designed to do one thing exceptionally well: retrieve and format citations. It is intended to be plugged into larger, more ambitious meta-prompting frameworks and AI agents to power their academic capabilities.

## 📄 License
MIT License
