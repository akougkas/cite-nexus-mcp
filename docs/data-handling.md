# Data handling and provider access

CiteNexus is a locally runnable MIT-licensed metadata service. The current project
does not operate a hosted research service, account system or application telemetry.

Selected provider APIs receive the search query or identifier needed for the operation.
For example, searching a private project title sends that title to each selected source.
Optional credentialed providers receive their configured authentication values. Unpaywall
receives a DOI and configured contact email for optional OA enrichment. Review each
[provider's terms and documentation](providers.md) before sending confidential queries.

Metadata responses are cached in process with bounded size and lifetime. Stopping the
server removes this cache. CiteNexus does not persist a bibliography, download full texts,
or send records to an LLM. Your MCP client receives returned metadata and may store it or
send it to its own model provider under that client's settings and policies.

API keys are configured outside tool arguments. Provider errors omit raw upstream bodies
and credential values. Source URLs and metadata are untrusted content; returned links are
for review, not instructions to execute. Arbitrary input URLs are not fetched.

The WTF-P companion forwards only selected provider credentials and runtime essentials,
ignores `.env` files, and starts a server per operation. It retains source provenance and
provider errors in the result. WTF-P separately controls research notes and project files.

The loopback HTTP transport has one local trust boundary. Public or multi-user deployment
requires authentication, credential isolation and operational controls that are not supplied
by the current CLI. Local plugin preparation is not a hosted-service privacy certification.

Software licensing does not grant redistribution rights over every upstream record or
subscription database. Keep attribution and follow the terms of the selected sources.
