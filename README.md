# Pleiades MCP

**The AI-Native Academic Citation & Research Engine**

[![Model Context Protocol](https://img.shields.io/badge/MCP-Enabled-blue.svg)](https://modelcontextprotocol.io/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Pleiades is a fast, lightweight Model Context Protocol (MCP) server designed to give AI agents (like Claude Code, Gemini CLI, Cursor, and Windsurf) native access to the global academic literature graph. 

Named after the famous star cluster (and the divine sisters of Greek mythology), Pleiades brings order to the chaotic universe of academic publishing. Rather than forcing researchers to break their writing flow to navigate web interfaces, Pleiades brings powerful reference management, citation generation, and metadata formatting directly into the IDEs and terminals where the writing actually happens.

---

## 🌟 The Vision

For decades, reference management has meant opening dedicated desktop applications (like Zotero or EndNote) or navigating browser-based walled gardens. While modern tools like Google Scholar Labs offer fantastic human-centric reading experiences, they remain isolated from the actual writing environment.

Pleiades takes a different approach: **Innovation through Integration.**

We believe the future of research is *Agentic*. Your AI assistant should be able to seamlessly fetch, format, and verify citations without you ever leaving your editor. Pleiades acts as the critical bridge between massive academic databases (like Google Scholar) and your local AI workflows. It doesn't compete with the giants of academic search; it unlocks their full potential for the AI era.

### Why Pleiades?
- **Cluster-First Architecture:** Uses Google Scholar "Cluster IDs" as the universal source of truth, bypassing the brittleness of DOIs, mismatched titles, or broken URLs.
- **LLM-Powered Formatting (Elicitation):** Replaces thousands of lines of fragile parsing code with dynamic AI formatting. Need a bespoke BibTeX format for a niche IEEE conference? Pleiades handles it gracefully.
- **Where You Write:** Integrates directly into your AI coding assistants, meta-prompting frameworks (like [WTF-P](https://github.com/akougkas/wtf-p)), and terminal agents. No more tab-switching.

---

## 🛠️ Core Capabilities

Pleiades exposes four focused MCP tools to your AI agent:

1. **`find-scholar-id`**: Converts any messy input (a loose title, an ArXiv ID, a DOI, or a fragmented citation) into a universal, stable Google Scholar Cluster ID.
2. **`get-citation`**: Fetches the complete metadata for a Cluster ID and generates a perfectly accurate BibTeX entry.
3. **`enhance-citation`**: Applies custom templates, rules, and notes to an existing citation (e.g., "Change to first-initial only", "Add a custom note regarding methodology").
4. **`paper-metrics`**: Retrieves impact analytics, citation counts, and top related papers to help your agent evaluate a source's significance.

---

## 🚀 Quickstart

Pleiades is packaged with `uv` for lightning-fast installation and execution.

### Prerequisites

You need a [SerpAPI Key](https://serpapi.com/) to query Google Scholar.

```bash
export SERP_API_KEY="your-serpapi-key"
```

**(Optional) Fallback API Configuration:**
If your primary MCP client (e.g., Claude Code, Gemini CLI) does not yet support native MCP Elicitation, Pleiades will automatically fall back to an OpenAI-compatible API to perform its data formatting.

```bash
export OPENAI_API_KEY="sk-..."
# Optional overrides for local models (Ollama, vLLM, etc.):
# export OPENAI_API_BASE="http://localhost:11434/v1" 
# export OPENAI_MODEL="llama3"
```

### Running via `uvx`

You can run the server instantly without permanently installing it into your global environment:

```bash
uvx pleiades-mcp
```

### IDE / Agent Integration Examples

#### Claude Desktop
Add Pleiades to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "pleiades": {
      "command": "uvx",
      "args": ["pleiades-mcp"],
      "env": {
        "SERP_API_KEY": "your-serp-api-key",
        "OPENAI_API_KEY": "your-openai-api-key-if-needed"
      }
    }
  }
}
```

#### Cursor / Windsurf
Provide the exact same command (`uvx pleiades-mcp`) and environment variables in the MCP configuration panel of your IDE settings.

---

## 🏗️ Development

To build on top of Pleiades or run it locally:

1. Install `uv`:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Clone and install:
   ```bash
   git clone https://github.com/akougkas/pleiades-mcp.git
   cd pleiades-mcp
   uv sync
   ```
3. Run the development server:
   ```bash
   uv run pleiades-mcp
   ```

---

## 🤝 Philosophy & The Future

Pleiades is built on the **"Engine in the Car"** philosophy. It is designed to be the ultimate citation engine that powers larger, more ambitious academic AI frameworks. As the academic ecosystem evolves, Pleiades will grow to encompass citation graph traversal, local library (PDF) syncing, and hallucination verification, empowering researchers to do their best work at the speed of thought.

## 📄 License
MIT License
