# Release preparation — 0.2.0

**Prepared locally. No release, tag, registry submission, marketplace claim or advertisement
is authorized by this preparation.** `release/product.json` records that state. The generation
scripts only write local metadata. CI does not publish automatically. A separate manual
`publish.yml` workflow requires finalized release state, an annotated tag and explicit
production confirmation before its protected PyPI publishing job can run.

Start with the [step-by-step 0.2.0 runbook](release-0.2.0.md). The
[WTF-P team handoff](wtfp-team-prompt.md) targets the separate `0.7.0` minor release.

See the [dated validation record](validation.md) for completed tests, artifact checks and
the exact scope of the remaining qualifications.

## Position and initial audience

CiteNexus is the source-backed research service for an assistant that already knows how to
write. Its immediate audience is researchers using MCP-enabled assistants and WTF-P, plus
teams that need the same evidence record across public and institutionally licensed sources.

Lead with a concrete workflow: **discover → resolve → verify → export → write with WTF-P**.
The first search should work without an account. Optional vendor keys extend coverage; they
are not the entrance requirement. Keep pricing statements at the correct boundary: the
software is MIT-licensed, default APIs need no key, and upstream quotas or licenses still apply.

Use [launch-kit.md](launch-kit.md) for copy and demos, and
[marketplaces.md](marketplaces.md) for the researched distribution queue. JSON and CSV sources
under `release/` retain evidence URLs, observed redirects and unresolved eligibility.

## Prepared assets

| Asset | Purpose |
|---|---|
| `release/product.json` | Canonical product name, descriptions, keywords, namespace and preparation state |
| `server.json` | Official MCP Registry metadata for the future PyPI 0.2.0 artifact |
| README `mcp-name` marker | PyPI package ownership evidence for `io.github.akougkas/cite-nexus-mcp` |
| `packaging/cite-nexus/` | Portable Agent Plugins 1.0 plus Codex/Claude compatibility manifests; local testing only |
| `assets/cite-nexus.svg` and `cite-nexus-400.png` | Vector source and 400×400 listing icon |
| `assets/social-card.svg` and `social-card.png` | Editable source and 1200×630 promotional image |
| `llms-install.md` | Explicit checkout installation steps for agents and Cline review |
| `docs/wtf-p.md` | Companion setup, workflow boundaries and removal instructions |
| `scripts/check_wtfp.py` | Generated WTF-P → companion → actual MCP stdio → fixture provider verification |
| `release/schemas/` | Pinned upstream schemas for offline validation, with attribution |

The registry schema version is **2025-12-11** as used by the current registry quickstart.
It is independent of the **2026-07-28** MCP wire specification. Do not rename one to match
the other. All generated versions derive from `pyproject.toml`.

## Local checks

```bash
uv sync --locked
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src/cite_nexus_mcp
uv run python scripts/prepare_release.py --check
uv run python scripts/marketplaces.py --check
uv run pytest -q
uv build
uv run cite-nexus-wtfp --check
uv run python scripts/check_wtfp.py --wtfp-root ../wtf-p
```

In WTF-P, regenerate from canonical sources, use its documented local commit/reseal workflow,
and run `npm run test:all`. Never hand-edit generated bundles or bypass the provenance checks.
The paired integration remains unreleased even if local source commits exist.

`scripts/marketplaces.py --probe` is a separate, explicit GET-only check of external links.
It does not change the curated tracker. Public-API smoke checks are also separate from the
offline suite. Paid provider entitlement checks require configured accounts and selected scope.

## Gates before a release decision

- [ ] Select final CiteNexus and WTF-P release versions and record their exact source commits.
  CiteNexus 0.2.0 and WTF-P's `Unreleased` section are preparation labels, not a release claim.
- [ ] Review the final diff, package manifests, lockfile, wheel and sdist contents. Keep private
  environment files and client settings out of artifacts. Verify the README marker survives
  wheel metadata generation. Recheck dependencies for disclosed vulnerabilities.
- [ ] Confirm a clean installed wheel starts MCP, exposes 11 tools, and runs the companion
  diagnostic. Run the paired generated-plugin fixture check and WTF-P's required evaluation.
- [ ] Qualify actual disposable client installations for every advertised host/OS. Current
  transport tests and schema checks do not certify native plugin lifecycle. In particular,
  perform Cline's required README-guided setup test and Windows/macOS companion checks.
- [ ] If choosing Docker, start a local daemon, build the image, exercise stdio through the
  container, and generate Docker's catalog entry against the exact commit. Docker packaging
  is not yet qualified merely because a Dockerfile exists.
- [ ] If choosing Smithery local distribution or Claude desktop extensions, build and test an
  MCPB artifact using the channel's current format. No MCPB artifact is prepared in this pass.
- [ ] Review live public-provider smoke outcomes. Treat throttling/outages as such. Qualify
  paid/institutional adapters with real entitlements before making live-access claims.
- [ ] Recheck marketplace routes and account/ownership requirements. Keep hosted ChatGPT/Codex
  public-directory submissions and remote connector routes deferred until authentication,
  credential isolation, hosting and review are implemented.
- [ ] Obtain a later explicit release instruction. Only then publish the Python artifact,
  verify its metadata, authenticate the matching registry namespace and submit `server.json`.
  Registry ownership validation depends on the already published PyPI artifact; offline JSON
  Schema validation cannot replace that step.
- [ ] Coordinate the WTF-P release separately. Do not tell users that npm 0.6.0 includes this
  integration. Submit initial P1 listings and send announcements only after installation works
  from the public artifacts and the user authorizes launch activity.

## Distribution sequence

1. Publish the approved versioned package and GitHub release assets, then register official
   MCP metadata. Keep public install commands pinned to that version.
2. Submit PulseMCP, MCP.so, MCPServers.org, Cline and the best-fitting curated list. Confirm
   Glama's claim/import route. Follow Docker and Smithery only after their packaging gates pass.
3. Verify each public listing and test the installation instructions it renders. Record URLs,
   submission dates and moderation outcomes in the tracker. Do not duplicate syndicated routes.
4. Announce the reproducible free-source demo and the paired WTF-P workflow. Use observed
   evidence and disclosed limits, not invented benchmarks, adoption numbers or guarantees.
5. Expand client packaging and hosted/institutional offerings in response to tested demand.

## Upstream references

- [Official registry quickstart](https://modelcontextprotocol.io/registry/quickstart) and
  [package ownership rules](https://modelcontextprotocol.io/registry/package-types)
- [Agent Plugins specification](https://agent-plugins.org)
- [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [Smithery publishing](https://smithery.ai/docs/build/publish)
- [Docker contribution process](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md)
- [Cline submission requirements](https://github.com/cline/mcp-marketplace)

Researched 2026-09-16. Submission policies can change before launch.
