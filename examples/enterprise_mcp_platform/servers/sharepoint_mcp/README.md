# SharePoint MCP Server

Owns only SharePoint and Microsoft Graph tool behavior.

Current tools:

- `sharepoint_list_site_content`
- `sharepoint_get_file_text`
- `sharepoint_upload_file(site_id, file_path, content)`

This server should not contain CRM, internal software, email, shell, database,
or generic HTTP tools.

`sharepoint_list_site_content` lists bounded metadata from the site's default
document library, follows Graph pagination, and optionally walks returned
folders. `sharepoint_get_file_text` accepts an already authorized `site_id`,
`drive_id`, and `item_id`; it verifies that the item belongs to that site before
downloading and extracting PDF text. It does not accept a caller-supplied URL.
PDF downloads are limited to 25 MiB and returned text remains bounded by the
caller's validated `max_chars` value. PDFs above 250 pages are rejected before
page text is extracted.

The write surface is one tool. It uploads UTF-8 content to the supplied path in
the site's default document library. Invalid `site_id` or `file_path` values
raise an error. The server does not trim, normalize, repair, or replace supplied
values; an empty string is valid content for an empty file.

The current repository implementation uses the same source and immutable
container image in two configured credential lanes:

- `sharepoint-delegated` uses `GRAPH_AUTH_MODE=obo`, requires the
  Gateway-provided
  `x-mcp-user-assertion` header and exchanges it through MSAL for a delegated
  Microsoft Graph token.
- `sharepoint-application` uses `GRAPH_AUTH_MODE=client_credentials`, obtains a
  Graph application token and does not accept a user assertion.

Both modes load the confidential-client secret lazily from the lane-specific
Secrets Manager ARN. Tokens and secrets are never logged. Live reads use Graph
metadata to enforce the supplied site boundary, then download through Graph's
short-lived preauthenticated URL without forwarding the Graph bearer token.
Those URLs are accepted only from the authenticated Graph metadata response,
must use HTTPS without embedded user information, and are never accepted as
tool inputs.
The upload adapter uses the Graph
`PUT /sites/{site-id}/drive/root:/{path}:/content` endpoint.

The image uses Python MCP SDK 2.0 `MCPServer` with stateless Streamable HTTP.
It listens on AgentCore Runtime's required `0.0.0.0:8000/mcp` path, and the
SharePoint pipeline builds the service image for `linux/arm64`.
The current released MCP specification is `2025-11-25`. The server targets the
`2026-07-28` release candidate for direct validation; managed AgentCore Gateway
dialect support remains unverified. Delegated and application lanes continue to
reuse one immutable image.

## Target identity-routing boundary

The current app-only lane uses direct client credentials but Gateway app-only
ingress is gated off. The accepted target keeps app-only semantics while the
Runtime obtains the Graph application token through a lane-scoped AgentCore
Identity M2M provider. It uses one application Runtime per approved trust domain
with a thin default-deny resolver. The platform resolver key is validated caller
client ID + exact target-qualified action + server-owned resource key +
environment; for this server the resource key remains `site_id`. Callers cannot
provide auth mode/provider alias/ARN/client ID/secret or `resource_ref`;
`site_id` is passed to Graph unchanged, and misses or unavailable
configuration/providers fail closed without provider disclosure.

The target delegated path uses two audience-specific AgentCore Identity OBO
hops (Gateway -> Runtime -> Graph), replacing the current interceptor/MSAL path
only after non-production validation. Delegated workload IAM allows only OBO
providers; application workload IAM allows only M2M providers. The official AWS
documentation does not provide the complete native no-code app-only caller-
context composition, and it remains unverified. See
[ADR 0012](../../../../docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md)
for the target gates.

When the staged `agentcore_m2m` branch is enabled, the application Runtime uses
the bounded `APP_ONLY_MAPPING_JSON` resolver and an explicit provider ARN
binding rather than a lane secret. Provider registration and credential method,
as well as caller application password/certificate/federated-credential
provisioning, remain outside this service and require approval before ingress is
enabled.
