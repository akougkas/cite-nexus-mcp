CiteNexus currently centers on paid Scholar access and AI-assisted citation formatting. This
change prepares version 0.2.0 as a scholarly metadata service with free default discovery,
source-backed reference checks and deterministic citation exports.

The implementation supports nine provider adapters, optional Unpaywall enrichment, structured
MCP tools, stdio and local Streamable HTTP. The separately installed WTF-P companion connects
the existing citation-search command through actual MCP stdio, retaining candidate status,
source attribution, provider issues and separate citation counts.

Release preparation includes registry/plugin metadata, installation and migration guidance,
launch assets, a researched marketplace inventory, artifact checks and a manual PyPI Trusted
Publishing workflow. Normal pushes and tag creation do not publish a package. The current
preparation state blocks publication until the owner finalizes the release and explicitly
dispatches the workflow against a reviewed annotated tag.

Validation evidence is recorded under `docs/release/validation.md` and
`docs/release/delivery-validation.md`. Run the newly added hosted OS matrix before claiming
macOS/Windows installed-package checks passed. Native client certification, Docker/MCPB
distribution, hosted connectors and live licensed-provider access remain separately scoped.

No PyPI package, GitHub release, registry entry, marketplace submission or announcement has
been published by this preparation. Operator-owned local client configuration and scratch
tests are excluded from this change.
