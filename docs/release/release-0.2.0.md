# CiteNexus 0.2.0 release runbook

Prepared 2026-09-17. The release has not been executed. These are ordered operator steps;
commands in the publication section change public state and are for a later approved launch.

## Release order and scope

1. Release **CiteNexus 0.2.0** as the Python package and source release.
2. Verify a clean public install and the `cite-nexus-wtfp` companion.
3. Have the WTF-P team integrate the prepared branch, qualify it against that installed
   package, and release **WTF-P 0.7.0**, the next minor after the current 0.6.0.
4. Register official MCP metadata and submit the selected launch listings after the
   public artifact is available. Announce the paired workflow after both releases work.

The initial CiteNexus release includes the local MCP service and optional companion.
Docker catalog distribution, MCPB installers, hosted connectors, native plugin listings,
and institution-specific entitlement certification are separate tracks. They need their
own tests before being advertised, but do not block the Python package release.

## Observed current state

| Item | Checked state |
|---|---|
| GitHub repository | Public `akougkas/cite-nexus-mcp`; default branch is **master** |
| Local preparation branch | `prep/citenexus-0.2.0` |
| PyPI project | Public JSON endpoint returned 404 on 2026-09-17; no public project was visible |
| GitHub releases/workflows | No published releases or remote workflows at the time checked |
| Intended package/version | `cite-nexus-mcp==0.2.0` |
| Registry identity | `io.github.akougkas/cite-nexus-mcp` |
| WTF-P package | npm `latest` is 0.6.0; intended next minor is 0.7.0 |
| Existing private/local changes | `.gemini/settings.json` and `test_safe_providers.py` are outside this release change |

A 404 does not guarantee that a package name can be registered. PyPI's pending publisher
does not reserve the name; recheck it at publication. Never overwrite another project's
identity or silently change the package name in only one manifest.

## 1. Review and land the prepared source

Review the CiteNexus preparation branch, including the earlier local commits it inherits,
against `origin/master`. The modernization now replaces the legacy paid-provider-first
implementation; review the migration notes and dependency changes as part of this release.
Preserve the operator-owned local files rather than staging them with a broad `git add .`.

After approval to send the branch for review:

```bash
git push -u origin prep/citenexus-0.2.0
gh pr create --repo akougkas/cite-nexus-mcp --base master \
  --head prep/citenexus-0.2.0 \
  --title "Prepare CiteNexus 0.2.0 scholarly research service and WTF-P companion" \
  --body-file docs/release/pr-body.md
```

The branch includes CI for Python 3.11–3.14 and isolated installed-wheel checks on
Linux/macOS/Windows. Local Linux checks are completed; the new hosted matrix must run
on the PR before claiming those additional OS checks passed. Merge only reviewed changes
with successful required checks. A push or merge does not publish anything.

## 2. Configure the first PyPI publisher (account owner)

Sign in to the intended maintainer account on PyPI and complete its account/2FA requirements.
Open [account publishing settings](https://pypi.org/manage/account/publishing/) and add a
**pending GitHub publisher** with these exact values:

| Form field | Value |
|---|---|
| PyPI project name | `cite-nexus-mcp` |
| GitHub owner | `akougkas` |
| Repository name | `cite-nexus-mcp` |
| Workflow filename | `publish.yml` (filename only) |
| Environment name | `pypi` |

In [GitHub repository environments](https://github.com/akougkas/cite-nexus-mcp/settings/environments),
create **pypi**, allow deployment from **master**, and configure a required reviewer if your
repository plan supports it. Permit the intended release operator to approve their own run
only if that matches your release policy. The workflow dispatch itself runs from `master`;
the build checks out the selected tag. Do not configure the environment to allow only tag
refs, because the workflow invocation ref is `master`.

The workflow uses GitHub OIDC through PyPI Trusted Publishing. No long-lived PyPI token needs
to be placed in the repository, copied into chat, or supplied as a workflow argument. GitHub
CLI authentication does not prove ownership or publishing access on PyPI.

Optional TestPyPI testing needs a separate TestPyPI account/pending publisher and environment;
it is not a prerequisite for this flow. Do not mix TestPyPI as a runtime dependency index.

## 3. Finalize the reviewed release text

Before tagging, make a final release commit that:

- Confirms 0.2.0 in `pyproject.toml`, `src/cite_nexus_mcp/__init__.py` and all generated
  manifests. Run `scripts/prepare_release.py` after changing version/product metadata.
- Dates `CHANGELOG.md` as `## 0.2.0 — YYYY-MM-DD` using the actual release date.
- Replaces the README preparation banner with the release status and pinned install command:
  `uvx --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --no-env-file`.
- Updates `llms-install.md`, the companion setup docs and plugin README to distinguish the
  released CiteNexus package from the still-pending WTF-P 0.7.0 release. Historical validation
  records and marketplace research dates remain historical; do not rewrite them as new proof.
- Sets `release/product.json` to `"stage": "release-ready"` and
  `"release_authorized": true` after the owner authorizes publication. These fields are a
  checked record of the decision, not a replacement for that decision.
- Reviews the [release notes draft](release-notes-0.2.0.md), fills the date/commit references,
  and removes its draft banner for publication. Keep unverified compatibility claims out.

Run the required checks on the final source:

```bash
uv sync --locked
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src/cite_nexus_mcp
uv run python scripts/prepare_release.py --check
uv run python scripts/marketplaces.py --check
uv run python scripts/release_gate.py
uv run pytest -q
uv build --out-dir dist/pypi
uv run python scripts/check_distribution.py --directory dist/pypi --install
uv run python scripts/check_wtfp.py --wtfp-root ../wtf-p
```

`dist/pypi` holds only the wheel and source distribution, plus uv's ignored build marker.
Keep plugin ZIPs, Git bundles, old versions and checksums outside it. The checker rejects
unexpected artifacts. Run the explicit public-provider smoke test separately and record
rate limits as outcomes. Paid-provider credentials are not needed for this release's core tests.

## 4. Publish the approved version

Use a clean checkout of the reviewed `master` commit. Avoid using the operator's dirty
development checkout for tag/publication checks. Confirm that no `v0.2.0` tag or PyPI 0.2.0
artifact already exists. Package versions are immutable; do not retag or try to overwrite one.

```bash
git switch master
git pull --ff-only
git tag -a v0.2.0 -m "CiteNexus 0.2.0"
uv run python scripts/release_gate.py --tag v0.2.0
git push origin v0.2.0
gh workflow run publish.yml --repo akougkas/cite-nexus-mcp --ref master \
  -f release_tag=v0.2.0 -f confirm_pypi=true
gh run list --repo akougkas/cite-nexus-mcp --workflow publish.yml --limit 5
```

Open the run, inspect its selected tag and commit, approve the `pypi` environment when
prompted, and watch that exact run with `gh run watch <run-id> --exit-status`. The workflow
checks the annotated tag, finalized release state and ancestry from `origin/master`, runs
tests, builds both distributions, and tests a fresh wheel installation. A separate job
downloads those same artifacts and publishes with OIDC and attestations. It does not publish
on a normal push, tag push or GitHub release event.

## 5. Verify the public package and create the GitHub release

After the workflow succeeds:

```bash
uvx --refresh --from cite-nexus-mcp==0.2.0 cite-nexus-mcp --version
uvx --refresh --from cite-nexus-mcp==0.2.0 cite-nexus-wtfp --check
```

Confirm the public PyPI page has the expected version, ownership marker, source links and
files. Exercise an actual MCP client against the installed package and one public-source
search. The WTF-P team should install this pinned package into its disposable test environment
and set `WTFP_CITE_NEXUS_COMMAND` to the installed companion executable.

Download the exact workflow artifacts, rather than rebuilding potentially different files:

```bash
gh run download <run-id> --repo akougkas/cite-nexus-mcp \
  --name pypi-distributions --dir dist/published-0.2.0
gh release create v0.2.0 --repo akougkas/cite-nexus-mcp --verify-tag \
  --title "CiteNexus 0.2.0" --notes-file docs/release/release-notes-0.2.0.md \
  dist/published-0.2.0/*.whl dist/published-0.2.0/*.tar.gz
```

If upload succeeds but a later verification fails, do not overwrite 0.2.0. Diagnose the
published artifact and prepare a patch version; use PyPI's documented yanking controls only
when justified. A partial publish must be inspected before retrying the workflow.

## 6. Registry and marketplace sequence

With the package publicly available, install a reviewed official `mcp-publisher` release.
From the exact release checkout:

```bash
mcp-publisher validate
mcp-publisher login github
mcp-publisher publish
```

Authenticate as the owner of the `io.github.akougkas` namespace. These registry commands are
separate public actions, not part of the PyPI workflow. Verify the published registry entry's
package version and installation arguments before submitting other listings.

Initial queue: **PulseMCP, MCP.so, MCPServers.org and a fitting curated research list**.
Cline follows its real README-guided installation attestation; Glama needs its listing/claim
route confirmed. Docker/Smithery/MCPB and hosted plugin directories follow only after their
specific packaging or hosting qualification. GitHub MCP Registry inclusion is not promised
to happen automatically. Track submissions once, avoiding duplicate syndicated channels.

Use [marketplaces.md](marketplaces.md), [launch-kit.md](launch-kit.md) and the machine-readable
tracker. Sending announcements is a separate launch action; no posts or emails were sent
during preparation.

## 7. WTF-P team handoff

Send [wtfp-team-prompt.md](wtfp-team-prompt.md), the local integration branch or the verified
Git bundle, and the CiteNexus release version/URL after public verification. The integration
branch was not pushed. Its source commit is `0b13a74`, its evaluation reseal is `2d26713`,
and its base is `3eac8b8`. A version bump changes generated envelopes, so the team must reseal
again after merging and generating the 0.7.0 packages.

## Sources checked

- [PyPI pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
  and its [upstream source](https://github.com/pypi/warehouse/blob/main/docs/user/trusted-publishers/creating-a-project-through-oidc.md)
- [Official PyPI publish action](https://github.com/pypa/gh-action-pypi-publish)
- [uv package publishing](https://docs.astral.sh/uv/guides/package/)
- [MCP Registry authentication](https://modelcontextprotocol.io/registry/authentication)
