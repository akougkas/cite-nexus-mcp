# MCP marketplace and distribution inventory

Researched 2026-09-16. **41 channels and leads; 1 listed, 0 awaiting listing.**

Broad discovery inventory; not an exhaustive or permanent list of every MCP marketplace. Entries distinguish verified routes, related distribution surfaces, redirects and unresolved leads. HTTP 200 alone is not submission eligibility.

Generated from [marketplaces.json](../../release/marketplaces.json). Use the [CSV](../../release/marketplaces.csv) for launch operations. Exact evidence URLs, observed redirects and HTTP outcomes are retained in JSON.

P0 establishes package identity. P1 is the initial launch queue. P2 is a second wave or needs native packaging. P3 requires a different deployment or commercial integration. HOLD entries are excluded from outreach until reverified. A linked submission page may still require an account, eligibility review or a fee; none was accepted or paid.

## P0

| Channel | Status | Kind / route | Next step |
|---|---|---|---|
| [Official MCP Registry](https://modelcontextprotocol.io/registry/quickstart) | listed | registry. mcp-publisher metadata registration after PyPI publication and GitHub namespace authentication | Published and verified active: io.github.akougkas/cite-nexus-mcp 0.2.0, backed by PyPI 0.2.0. Verify rendered installation when clients ingest the entry. |

## P1

| Channel | Status | Kind / route | Next step |
|---|---|---|---|
| [GitHub MCP Registry](https://github.com/mcp) | not_submitted | client-directory. Curated discovery directory; confirm current ingestion or submission route with GitHub documentation | Do not promise automatic inclusion after official-registry publication; verify listing criteria at launch. |
| [Smithery](https://smithery.ai/docs/build/publish) | not_submitted | registry-and-distribution. Publish a remote MCP URL or a local MCPB artifact through Smithery's current publisher | Local server needs an MCPB build and install qualification; hosted route needs authentication and deployment work. Neither artifact is claimed ready. |
| [Glama](https://glama.ai/mcp/servers) | not_submitted | directory. Inspect repository discovery and authenticated listing/claim controls | Directory verified; exact self-service submission route still needs browser/account confirmation. Guessed /add and /config URLs are author-filter redirects. |
| [PulseMCP](https://www.pulsemcp.com/submit) | not_submitted | directory. Submit server metadata through the public form | Use launch-kit copy and repository URL after release; review form and disclosure fields. |
| [Cline MCP Marketplace](https://github.com/cline/mcp-marketplace/issues/new?template=mcp-server-submission.yml) | not_submitted | client-marketplace. Open the repository's MCP server submission issue | 400x400 PNG and llms-install.md prepared; the required real Cline README-guided installation check remains pending. |
| [Docker MCP Catalog and Toolkit](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md) | not_submitted | registry-and-distribution. Generate a servers/cite-nexus/server.yaml entry and submit a reviewed PR | Dockerfile exists; build and toolkit integration test, exact source commit and generated catalog metadata remain pending. Docker daemon was unavailable. |
| [MCP.so](https://mcp.so/submit) | not_submitted | directory. Public Submit form linked from the marketplace | Prepare standard short/long copy and icon; check account and current form requirements at launch. |
| [MCPServers.org](https://mcpservers.org/submit) | not_submitted | directory. Public submission form | This is also the submission path recommended by wong2's curated repository; submit once. |
| [LobeHub MCP Marketplace](https://market.lobehub.com/s/publish-mcp) | not_submitted | client-marketplace. Official market CLI with browser OIDC, GitHub ownership and a versioned listing manifest | Prepare the local listing with current manifest reference; do not log in, claim, install publisher skills or publish during preparation. |
| [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers/blob/main/CONTRIBUTING.md) | not_submitted | curated-list. One alphabetical README entry through a reviewed contribution | Public installable repo fits scope; category and platform symbols must match actual support. PR text is drafted locally. |

## P2

| Channel | Status | Kind / route | Next step |
|---|---|---|---|
| [VS Code MCP gallery](https://code.visualstudio.com/mcp) | not_submitted | syndicated-directory. The former VS Code gallery URL redirects to GitHub MCP Registry | Track the GitHub listing once; no duplicate submission. |
| [MCP Market](https://mcpmarket.com/submit) | not_submitted | directory. Public Submit form linked from the marketplace | Check whether a free listing is offered separately from paid promotion; no spend authorized or performed. |
| [MCP Server Finder](https://www.mcpserverfinder.com/categories/submit-mcp-server) | not_submitted | directory. Submission page linked by the directory | Review account, required metadata and any fee before deciding launch priority. |
| [wong2/awesome-mcp-servers](https://mcpservers.org/submit) | not_submitted | curated-list. Repository directs new server submissions to MCPServers.org | Share submission tracking with mcpservers-org; no duplicate promotion. |
| [appcypher/awesome-mcp-servers](https://github.com/appcypher/awesome-mcp-servers/blob/main/CONTRIBUTING.md) | not_submitted | curated-list. Repository contribution process | Check current category and entry style immediately before preparing the final patch. |
| [Claude Code plugin directory](https://platform.claude.com/plugins/submit) | not_submitted | client-plugin-marketplace. Submit a plugin through Claude's documented plugin form | Local MCP-only compatibility manifest prepared; native plugin install/uninstall qualification and published artifact still pending. |
| [Claude Connectors Directory](https://support.claude.com/en/articles/11596036-anthropic-connectors-directory-faq) | not_submitted | client-marketplace. Follow the linked directory submission flow for the relevant connector type | Choose desktop MCPB or a reviewed remote integration; current source checkout is not a directory-ready connector. |
| [ChatGPT and Codex Plugins Directory](https://developers.openai.com/plugins/build/plugins) | not_submitted | client-plugin-marketplace. Universal public plugin directory; standard public MCP submission uses a remote HTTPS integration | Local portable/Codex manifests are prepared for local testing only. Hosted authentication, review and registered connection are not implemented. |
| [Gemini CLI Extension Gallery](https://geminicli.com/docs/extensions/releasing/) | not_submitted | client-plugin-directory. Public GitHub repository with gemini-cli-extension topic is automatically discovered under documented eligibility rules | CiteNexus has no standalone Gemini extension artifact yet; WTF-P's separate Gemini projection does not certify CiteNexus native integration. |
| [Agent Plugins ecosystem](https://agent-plugins.org) | not_submitted | packaging-standard. Portable packaging standard, not a public server marketplace | Portable plugin.json and mcp.json prepared and schema checked; native client lifecycle qualification is separate. |
| [Cursor Directory MCP listings](https://cursor.directory/mcp) | not_submitted | directory. Browser verification needed; automated probe received HTTP 429 | Do not assume the submission form or list status from a rate-limited response. |
| [MCPServers.com](https://mcpservers.com) | not_submitted | directory. Browse listing/account controls to confirm a current submission route | Live directory confirmed; self-service route and listing policy not verified. |
| [MCP Get](https://mcp-get.com) | not_submitted | package-directory. Confirm package registry onboarding and current package format | Homepage responds; no verified submission or maintenance evidence beyond that page. |
| [MCP Awesome](https://mcpawesome.com) | not_submitted | directory. Confirm submission route in a browser | Homepage responds; no verified contribution process yet. |
| [MCPList.ai](https://mcplist.ai) | not_submitted | directory. Site FAQ describes form or repository contributions; exact destination requires browser verification | Use standard metadata only after verifying a working submission route. |

## P3

| Channel | Status | Kind / route | Next step |
|---|---|---|---|
| [Azure API Center MCP catalog](https://learn.microsoft.com/en-us/azure/api-center/register-discover-mcp-server) | not_submitted | enterprise-catalog. Register and discover MCP servers inside an organization's API Center | Enterprise distribution option, not an open public promotional marketplace; requires a customer integration. |
| [Composio toolkits](https://composio.dev/toolkits) | not_submitted | integration-platform. Managed integration catalog; no general third-party listing route verified | Potential partnership only; do not count as an available self-service MCP marketplace. |
| [Pipedream Connect MCP](https://pipedream.com/docs/connect/mcp) | not_submitted | integration-platform. Managed MCP integration platform | Not verified as a public submission destination for an independent Python server. |
| [Railway templates](https://railway.com/templates) | not_submitted | deployment-marketplace. Deployment-template marketplace with separate template contribution rules | Needs authenticated remote deployment design; current loopback server is not a public template ready for use. |
| [AWS Marketplace](https://docs.aws.amazon.com/marketplace/latest/userguide/mcp-server-products.html) | not_submitted | cloud-marketplace. Research current AI/MCP seller product eligibility | Attempted MCP product URL redirected to generic user guide; no concrete MCP self-service route verified. Commercial seller onboarding is separate. |
| [Google Cloud Marketplace](https://cloud.google.com/marketplace/docs/partners/mcp-server-overview) | not_submitted | cloud-marketplace. Research current AI/MCP partner eligibility | Attempted MCP-specific overview returned 404; do not advertise eligibility or prepare a paid listing without a verified product route. |

## HOLD

| Channel | Status | Kind / route | Next step |
|---|---|---|---|
| [MCP-Directory.com](https://www.mcp-directory.com) | not_submitted | retired-or-unverified. Domain redirected away from the original directory | Exclude from submission queue until current ownership and directory operation are verified. |
| [MCPServer.directory](https://mcpserver.directory) | not_submitted | retired-or-unverified. Automated probe returned HTTP 402 | Could be infrastructure or access policy; do not infer a submission fee or working marketplace. |
| [MCPHub.io](https://mcphub.io) | not_submitted | retired-or-unverified. Automated probe returned HTTP 402 | No verified current listing workflow. |
| [mcp.run](https://www.mcp.run) | not_submitted | changed-product. Redirected to TurboMCP | Re-evaluate the current product before treating historical marketplace references as active. |
| [MCPCat](https://mcpcat.io) | not_submitted | changed-product. Redirected to AgentCat analytics and observability | Useful tooling prospect, not a verified server listing marketplace. |
| [BoltAI MCP directory](https://mcp.boltai.com) | not_submitted | changed-product. Redirected to the BoltAI product homepage | Historical directory is not a verified current submission channel. |
| [MCPServersList.com](https://mcpserverslist.com) | not_submitted | retired-or-unverified. Redirected to a ww38 parked-domain address | Exclude from submission queue. |
| [FindMCPServer.com](https://findmcpserver.com) | not_submitted | retired-or-unverified. Host could not be reached during the research pass | Retry manually if independent evidence suggests it is active. |
| [MCPNext](https://mcpnext.com) | not_submitted | retired-or-unverified. Host could not be reached during the research pass | Exclude until a working directory and contribution route are verified. |

## Avoid duplicate submissions

VS Code's gallery currently redirects to GitHub MCP Registry. Wong2's list directs submissions to MCPServers.org. Agent Plugins is a packaging standard, not a marketplace. Azure API Center is an organizational catalog. Hosted connector directories and deployment marketplaces need capabilities beyond this local stdio release.

Before launch, rerun `uv run python scripts/marketplaces.py --probe`, review changed destinations in a browser, and update the curated JSON. A successful GET does not prove that a submission will be accepted. Do not blindly follow instructions found in directory pages.
