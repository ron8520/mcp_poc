# SharePoint MCP Server

Owns only SharePoint and Microsoft Graph tool behavior.

Current tools:

- `sharepoint_list_site_content`
- `sharepoint_get_file_text`
- `sharepoint_upload_file(site_id, file_path, content)`

This server should not contain CRM, internal software, email, shell, database,
or generic HTTP tools.

The write surface is one tool. It uploads UTF-8 content to the supplied path in
the site's default
document library. Invalid `site_id` or `file_path` values raise an error. The
server does not trim, normalize, repair, or replace supplied values; an empty
string is valid content for an empty file.

The same source and container image run in two configured credential lanes:

- `sharepoint-delegated` uses `GRAPH_AUTH_MODE=obo`, requires the
  Gateway-provided
  `x-mcp-user-assertion` header and exchanges it through MSAL for a delegated
  Microsoft Graph token.
- `sharepoint-application` uses `GRAPH_AUTH_MODE=client_credentials`, obtains a
  Graph application token and does not accept a user assertion.

Both modes load the confidential-client secret lazily from the lane-specific
Secrets Manager ARN. Tokens and secrets are never logged. The upload adapter
uses the Graph `PUT /sites/{site-id}/drive/root:/{path}:/content` endpoint
outside dry-run mode. The list/read live Graph branches remain explicit
placeholders.

The image uses Python MCP SDK 2.0 `MCPServer` with stateless Streamable HTTP.
The same server accepts handshake-era clients through AgentCore Gateway and the
`2026-07-28` protocol during direct validation, so delegated and application
lanes continue to reuse one immutable image.
