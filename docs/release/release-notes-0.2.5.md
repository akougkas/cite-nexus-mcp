# CiteNexus 0.2.5

Release date: 2026-11-15. Source: annotated tag `v0.2.5`.

CiteNexus 0.2.5 follows a live WTF-P and Clio run with a 27B local model. The model spent about
20K tokens of a 131K context on three `search-papers` calls, called `verify-citation` with an
unknown `identifier` argument, and read `status: "verified"` as evidence that a paper supports a
claim. A WTF-P companion query returned 52 KB, and an arXiv search ranked an unrelated survey first.

## Changes

- `search-papers`: `limit_total` caps records across providers; `detail: "minimal"` returns only
  id, title, year, first three authors, venue and DOI/arXiv/PMID. `limit` is documented as per provider.
- `verify-citation`: `identifier` is accepted as an alias of `citation`. Results include `match`
  (`identifier` or `metadata`) and `claim_support: "not_checked"`.
- Records without an abstract carry `abstract: null` and `abstract_missing_reason`.
- Every tool description includes one example call.
- WTF-P companion: `detail` and `limit_total` request fields pass through to `search-papers` and
  are echoed in metadata. The default (`full`) output is unchanged.
- arXiv: plain queries require every non-stopword term instead of OR-ing all but the first.
- Provider guidance recommends `arxiv` and `semantic_scholar` for computer-science queries.
- README: Clio `mcp.yaml` declaration with per-tool read classes, and the plugin-scope
  `clio-coder mcp trust cite-nexus --network` step.

## Install

```bash
uvx --from cite-nexus-mcp==0.2.5 cite-nexus-mcp --no-env-file
uvx --from cite-nexus-mcp==0.2.5 cite-nexus-wtfp --check
```

See the [changelog](https://github.com/PanStudio/pancite/blob/v0.2.5/CHANGELOG.md) and [documentation](https://github.com/PanStudio/pancite/blob/v0.2.5/README.md) for further details.
