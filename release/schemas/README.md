# Pinned release schemas

Retrieved 2026-09-16 for offline validation. Files are copied unchanged from:

- `server-2025-12-11.json`:
  https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json
  (modelcontextprotocol/registry; its current mixed licensing transition notice is
  preserved in `MCP-REGISTRY-LICENSE.txt`).
- `plugin-1.0.0.json`:
  https://agent-plugins.org/schemas/1.0.0/plugin.schema.json
- `mcp-1.0.0.json`:
  https://agent-plugins.org/schemas/1.0.0/mcp.schema.json

Agent Plugins schemas are Apache-2.0 software material under the upstream
[licensing policy](https://github.com/agentplugins/agent-plugins-spec/blob/main/LICENSE.md);
the license is preserved in `AGENT-PLUGINS-LICENSE.txt`. These schemas retain their upstream `$id` and version. Update them deliberately,
then revalidate manifests; MCP wire-protocol version and registry schema version are separate.
