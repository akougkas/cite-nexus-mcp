# Setup and troubleshooting

## The command waits without printing a search result

`cite-nexus-mcp` is an MCP stdio server. Your client sends protocol messages to it;
it is not a search shell. Use `--list-providers` for a local configuration check or
`cite-nexus-wtfp --check` to test a complete MCP client/server handshake without API calls.

## The client starts an old release

The prepared code is 0.2.1. Run `uv run cite-nexus-mcp --version` inside this checkout.
Use the README's absolute `uv --directory ... run --locked` configuration until release.
Avoid unpinned `uvx cite-nexus-mcp` when trying unreleased features. Restart the client's
server connection after changing its command or upgrading the installed package.

## A client cannot find uv or the companion executable

Desktop clients may have a different PATH from your terminal. Give the client an
absolute executable path. For WTF-P, `WTFP_CITE_NEXUS_COMMAND` must be an absolute path
or the default installed `cite-nexus-wtfp` command; it cannot contain shell arguments.
Keep paths as separate JSON arguments, including paths containing spaces.

## A configured key appears unavailable

Keys belong in the server process environment, or in an explicitly selected `.env`
file for the standalone server. Existing process variables take precedence. The
bridge and prepared native plugin ignore `.env` files. `list-providers` reports
configuration only; an available adapter can still lack quota or institutional access.

## Search returns some results and errors

Inspect `issues` in native CiteNexus or `metadata.errors` in WTF-P. One provider can fail
while others return results, and `metadata.errors` records it. Partial failures
are expected when one source throttles or is unavailable. Anonymous Semantic Scholar
may return HTTP 429; select another suitable public source or use your own key.
An outage is not evidence that a reference does not exist. Retry after the indicated
cooldown, with fewer sources or a narrower query when appropriate.

## Search finds fewer papers than the limit

Native limits are per provider and filters apply to the fetched page. Year and OA
filters exclude records with unknown values. Deduplication reduces displayed counts.
Use the returned per-provider offset or Europe PMC cursor with the same query and
limit. WTF-P caps the displayed total and records truncation; use the native tool
for exhaustive page review.

## A reference is ambiguous, incomplete or mismatched

A title-only match remains ambiguous. Supply the DOI or namespaced identifier and
compare title/year explicitly with `verify-citation`. Missing authors are not inferred;
an incomplete author list warns and uses `others` in BibTeX where appropriate. Review
the publisher record before adopting corrections. Verification checks metadata identity,
not whether a paper supports a manuscript claim.

## WTF-P reports that the action is unavailable

Use the prepared WTF-P checkout and a host with its bounded dispatcher binding.
Clio and Claude Code currently have that binding. The companion does not remove
blockers on other hosts. Native CiteNexus MCP tools may still be configured directly
in those clients, independently of the WTF-P workflow's availability contract.

## Preparing an issue

Include package/Python/client versions, transport, provider IDs, a public minimal
query or identifier, and sanitized error codes. Remove keys, tokens, private
manuscript text and environment files. The [issue form](../.github/ISSUE_TEMPLATE/bug.yml)
collects these details. Do not paste full client logs without reviewing them.
