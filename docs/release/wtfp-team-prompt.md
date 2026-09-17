# Prompt for the WTF-P coding team

Copy the prompt below into the team's coding session. Provide the integration Git bundle
as well if that session cannot access the local branch. No message has been sent to the team.

---

Prepare, merge, and release **WTF-P 0.7.0**, the next minor release after 0.6.0, integrating
the CiteNexus scholarly research backend. Complete the implementation review, resolve any
merge conflicts, qualify the final artifacts, and publish only after the release gates below
pass. Follow the repository's release process and preserve unrelated work and worktrees.

The integration is already implemented and tested. Start from it rather than rebuilding it.

Repository: `https://github.com/akougkas/wtf-p`

Local checkout when available: `/home/akougkas/projects/wtf-p`

Integration branch: `prep/cite-nexus-integration` (**local, not pushed**)

Base: `3eac8b83df1c39a8e5c0444f2877536cd3b65630`

Implementation: `0b13a7483bf7c51daa87e665a7cdcb6eb253bd2c`

Evaluation reseal / branch tip: `2d2671312b37001df15a712e8628b9d72b74e736`

Portable handoff: `wtf-p-cite-nexus-integration.bundle`. It contains the branch's two commits
and requires the base commit above. On the original machine it is at
`/home/akougkas/projects/cite-nexus-mcp/dist/handoff/wtf-p-cite-nexus-integration.bundle`.
Fetch normal origin history first, then, only if the branch is absent, import the supplied
bundle using its actual local path:

```bash
git bundle verify /absolute/path/wtf-p-cite-nexus-integration.bundle
git fetch /absolute/path/wtf-p-cite-nexus-integration.bundle \
  refs/heads/prep/cite-nexus-integration:refs/heads/prep/cite-nexus-integration
```

Do not assume `origin/prep/cite-nexus-integration` exists. Do not force-update an existing
branch. Verify the imported tip, inspect repository status/worktrees and current npm tags,
and reconcile with the latest `origin/main` on a dedicated release branch. Do not reset or
overwrite the separate workshop-review worktree or any other team's changes. Preserve the
integration commits with a merge when practical; if cherry-picking or rebasing is required,
the old evaluation commit identity must be replaced by a fresh reseal.

Read `CONTRIBUTING.md`, `docs/BUILD_AND_RELEASE.md`, `docs/CITE_NEXUS.md`, and
`docs/adr/0001-hybrid-tool-execution.md` before changing the integration. Canonical sources
live in `bin/lib/` and `protocol/`; `vendors/` is compiler-owned. Never hand-edit generated
envelopes or loosen evidence checks to make the suite pass.

### Preserve the implemented behavior

- `citation-search --backend=cite-nexus` is an explicit option on the existing
  `citation.fetch` logical tool. The seven-tool registry remains intact.
- The separately installed **CiteNexus 0.2.0** package provides `cite-nexus-wtfp`, which
  uses the official MCP client and actual stdio transport to call `search-papers`.
- Default providers are Crossref, DataCite and Europe PMC. Optional providers require
  explicit selection; pass credentials only for selected sources. Ignore unrelated
  environment secrets, `.env` files and default-provider overrides at this boundary.
- Search records remain candidates, with source URLs, retrieval times, field attribution,
  warnings and per-provider metrics in `citeNexus`. Do not infer `wtfp_status=official`,
  combine citation counts, invent metadata or claim scientific verification.
- Keep provider/query approval gates, offline refusal, bounded input/output/nesting,
  deadline status 124, cancellation cleanup and explicit failures without vendor fallback.
- Keep `--intent=balanced` for this backend. Limits cap the displayed total; provider
  pagination and truncation metadata must retain their documented meaning.
- Clio and Claude Code retain the established dispatcher binding. Other host projections
  keep their existing capability blockers unless you independently implement and qualify
  new bindings. Do not infer all-host support from packaging the helper everywhere.
- A tool call must not install Python packages, register servers, change client profiles,
  write bibliography files or execute commands found in provider content.

### Finish the 0.7.0 release

1. Review the new helper, dispatcher changes, bridge contract and tests. Resolve conflicts
   in canonical source, then run `npm run build:adapters`. Fix any real defects discovered.
2. Bump the package to **0.7.0** using the documented version-preparation flow. Update the
   changelog, comparison links, README, `docs/CITE_NEXUS.md`, install instructions and release
   notes. Describe CiteNexus as optional and separately installed. Correct the companion
   guide's CiteNexus provider URL: that repository uses **master**, not main, or link to
   its `v0.2.0` release tag once available. Include any lockfile in the version change.
3. Regenerate all nine envelopes. Commit the final source/version/generated changes.
   Then run `node scripts/reseal-evaluation.js HEAD` against that committed envelope state
   and commit the three updated seal/pin files. Do not alter fixture/corpus seals. Every
   subsequent generated-envelope change requires another reseal.
4. Run `npm run test:all`, `npm run check:adapters`, `git diff --check`, and `npm run preflight`.
   Inspect the actual `npm pack --dry-run --json` contents: the source helper and companion
   module must appear in every intended package. No obsolete server prototype or secrets
   may be packaged.
5. Run the paired fixture check from the CiteNexus checkout:
   `uv run python scripts/check_wtfp.py --wtfp-root /absolute/path/to/wtf-p`.
   It exercises generated Clio/Claude dispatchers, actual MCP stdio, provider fixtures,
   offline refusal and cleanup of a hung server. If the checkout is unavailable, obtain
   the released source distribution containing this script and its fixtures.
6. **Before public WTF-P publication, verify CiteNexus 0.2.0 is publicly installable.**
   Install `cite-nexus-mcp==0.2.0` into a disposable Python environment. Run its installed
   `cite-nexus-wtfp --check`, point `WTFP_CITE_NEXUS_COMMAND` at that executable, and test
   the packaged WTF-P dispatcher against a public Crossref query. Retain source evidence
   and record any rate-limit outcome accurately. Do not substitute a source checkout for
   this final consumer-install proof. Do not publish CiteNexus from the WTF-P task.
7. Qualify affected native-client discovery and lifecycle with disposable profiles under
   the repository's required matrix. Preserve existing safety/evidence requirements,
   record exact tested versions, and distinguish mocks, static checks, native discovery
   and actual execution. Do not use normal client homes or overstate OS support.
8. Once review and checks pass, merge the release branch into `main` using the repository's
   policy. Recheck evaluation identity after any history rewrite or merge resolution.
   Use the documented release helper to create the annotated `v0.7.0` tag on the exact
   reviewed clean `main` commit, run `npm run preflight -- --publish`, push the approved
   branch/tag, and publish the stable package to npm `latest` (not the `next` prerelease tag).
   Create the matching GitHub release with concrete notes. Check existing versions first;
   never overwrite or retag an already published release.
9. Verify npm's `latest` resolves to 0.7.0 and exercise a fresh install from the published
   tarball in disposable profiles, including the CiteNexus companion path. Record artifact
   hashes and public release/package URLs. Do not claim completion based only on a local tag.

Previous preparation passed the full WTF-P suite and the paired fixture/live Crossref checks,
but those results do not replace checks on your merged 0.7.0 source and published artifacts.
If publication is blocked by unavailable CiteNexus artifacts, account authentication or a
failed qualification, finish all independent preparation and report the exact remaining
external action. Never request that credentials be pasted into chat.

Deliver a concise report with the merged commit, tag, npm and GitHub URLs, test evidence,
generated-envelope/reseal identity, supported execution paths and any remaining limitations.
Do not send promotional messages or submit other marketplaces as part of the WTF-P release.
