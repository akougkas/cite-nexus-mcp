# CiteNexus 0.2.4

Release date: 2026-11-10. Source: annotated tag `v0.2.4`.

CiteNexus 0.2.3 was tagged but never published to PyPI: its distribution check expected nine providers
while the package lists ten. CiteNexus 0.2.4 fixes the check and is the first published release with
the SearchApi.io (`searchapi`) Google Scholar provider introduced in 0.2.3.

## Fixes

- The installed-wheel distribution check compares the providers reported by `cite-nexus-wtfp --check`
  with the providers the installed package lists, instead of a fixed count.

## Install

```bash
uvx --from cite-nexus-mcp==0.2.4 cite-nexus-mcp --no-env-file
uvx --from cite-nexus-mcp==0.2.4 cite-nexus-wtfp --check
```

See the [changelog](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.4/CHANGELOG.md) and [documentation](https://github.com/akougkas/cite-nexus-mcp/blob/v0.2.4/README.md) for further details.
