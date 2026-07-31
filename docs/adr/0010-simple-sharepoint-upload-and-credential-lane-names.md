# ADR 0010: Simple SharePoint Upload and Credential-Mode Lane Names

Date: 2026-07-31

Status: Accepted

## Context

The SharePoint write surface had grown into separate page-insert and
file-update tools with change-ticket, idempotency, audit-reason, ETag,
correlation, and input-normalization rules. Those controls were added as
general enterprise-safety recommendations; they were not requirements for this
PoC. The existing list and read tools are not changed by this decision.

The existing `sharepoint-user` and `sharepoint-automation` names also describe
who or what appears to call the platform. The actual reason for two Runtime
lanes is the Microsoft Graph credential used downstream: delegated access on
behalf of a signed-in user versus app-only access with the application's own
identity.

AgentCore Gateway exposes an MCP tool using the AWS-defined
`<TargetName>___<ToolName>` format. The three underscores are therefore not a
repository naming convention or an extra SharePoint namespace.

## Decision

Expose one SharePoint write tool:

```text
sharepoint_upload_file(site_id, file_path, content)
```

The tool uploads the supplied UTF-8 content to `file_path` in the target site's
default document library.

- `site_id`, `file_path`, and `content` are the complete client-visible input
  contract.
- Invalid input raises an error immediately.
- The server does not trim, normalize, repair, coerce, or replace invalid
  input.
- The PoC does not require a change ticket, idempotency key, audit reason,
  expected ETag, or caller-supplied correlation ID.
- Direct Cedar still authorizes the exact target-qualified upload tool.
- SharePoint remains the resource-authorization boundary: delegated calls use
  the signed-in user's native SharePoint permissions; app-only calls use the
  application's explicit `Sites.Selected` grant.

Rename the SharePoint Runtime and Gateway target lanes:

1. `sharepoint-delegated`
   - uses Microsoft Graph delegated access through OBO;
   - acts within the signed-in user's SharePoint permissions.
2. `sharepoint-application`
   - uses Microsoft Graph app-only access through client credentials;
   - acts within the application's Graph permissions and `Sites.Selected`
     grants.

The corresponding AgentCore Gateway tool names and Cedar actions are:

```text
sharepoint-delegated___sharepoint_upload_file
sharepoint-application___sharepoint_upload_file
```

`___` must remain because AgentCore Gateway constructs MCP tool names as
`<TargetName>___<ToolName>`. It is not replaced with one underscore or a custom
separator.

Each exact action is bound to the concrete Gateway ARN in Cedar. Terraform
replaces the source placeholder during deployment because AgentCore requires a
specific Gateway resource when a policy names a specific action.

## Consequences

Positive:

- The SharePoint PoC now matches the requested capability instead of modelling
  a generic publishing workflow.
- Invalid values remain visible to the caller and are not silently changed
  into a different request.
- Lane names state the security property that causes separate deployments.
- Cedar action names remain predictable from the Gateway target and MCP tool.

Tradeoffs:

- This PoC does not provide duplicate-write suppression or optimistic
  concurrency for overwriting an existing file.
- A later production requirement for version-aware overwrite, workflow
  approval, or replay handling must be introduced explicitly and recorded in a
  new ADR rather than assumed by the example.
- Renaming targets changes the externally visible Gateway tool names, Cedar
  action identifiers, Runtime configuration, tests, and diagrams together.

## Validation

- A valid request uploads the supplied content at the supplied path.
- Missing or invalid required input fails with an error and is not modified.
  Empty `content` remains valid and creates an empty file.
- Neither lane accepts ticket, idempotency, audit-reason, ETag, or correlation
  fields as part of the upload contract.
- Cedar permits only the exact lane-qualified upload action.
- A delegated call is limited by the user's SharePoint ACL.
- An application call is limited by its `Sites.Selected` grant.

## Supersedes

This ADR supersedes the SharePoint lane names and write-tool contract in ADR
0006, and the SharePoint/CRM example lane names in ADR 0007. Their decisions to
separate materially different downstream credential modes, reuse one immutable
service image, use OBO for delegated access, use a separate application
identity for app-only access, and keep direct Cedar as the caller/tool policy
remain in force.

This ADR also replaces the SharePoint target names referenced by ADR 0009; its
vendor-native and documentation-target decision is unchanged.

## References

- [AWS AgentCore Gateway tool naming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html)
- [AWS AgentCore policy action scope](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-scope.html)
- [Microsoft Graph permission types](https://learn.microsoft.com/en-us/graph/permissions-overview)
