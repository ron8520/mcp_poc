# Direct Cedar Policy

The files under `cedar/` are the reviewed authorization source for AgentCore
Gateway. There is no intermediate YAML model, generated JSON bundle, or
Runtime-side copy of the authorization rules.

The policy boundary is intentionally narrow:

- Cedar decides whether a validated caller may discover or invoke an exact MCP
  tool.
- The SharePoint delegated lane uses Microsoft Graph on-behalf-of (OBO).
  SharePoint therefore decides which sites and items the signed-in employee may
  access.
- The SharePoint application lane uses a separate Graph application identity.
  `Sites.Selected` grants define the sites that identity may access.
- The upload tool accepts only the upload fields and rejects invalid input
  without trimming, normalizing, repairing, or substituting it.

## Files

- `cedar/sharepoint-delegated.cedar`: delegated access to the
  `sharepoint-delegated` Gateway target.
- `cedar/sharepoint-application.cedar`: app-only access to the
  `sharepoint-application` Gateway target.

The target names in Cedar are part of the authorization contract. Rename a
Gateway target and its matching Cedar actions in the same reviewed change.
AgentCore Gateway constructs each aggregated MCP tool name as
`<TargetName>___<ToolName>`, so the three underscores are an AWS-defined
separator.
Each policy binds its exact action to a concrete Gateway ARN. Terraform replaces
the reviewed `__GATEWAY_ARN__` placeholder because AgentCore requires a
specific Gateway resource for a specific action.

## Deployment

Terraform passes these Cedar statements directly to
`aws_bedrockagentcore_policy` and sets policy validation to
`FAIL_ON_ANY_FINDINGS`. AgentCore then validates the Cedar against the live
Gateway-generated schema during create or update.

The dual-lane Terraform keeps the Gateway-level `mcp.invoke` gate as a
fail-closed transition control while
`gateway_app_only_ingress_enabled = false`. Set that switch to `true` only in
the same approved rollout that promotes Cedar to `ENFORCE`. Terraform blocks
the switch in `LOG_ONLY`. Cedar then requires `mcp.invoke` for delegated actions
and an application app role for app-only actions.

Promote policy changes through:

1. source checks and security/data-owner review;
2. non-production policy update in `LOG_ONLY`;
3. positive and negative calls through the real Gateway;
4. promotion to `ENFORCE`; and
5. the normal production change gate.

Do not commit generated AgentCore schema or translated policy artifacts. They
may be retained as short-lived CI evidence when useful.

## Claims

Gateway validates issuer, audience, expiry, and approved client IDs. Cedar then
distinguishes:

- delegated callers by `scp` plus the
  `MCP.SharePoint.Delegated.Read` or `MCP.SharePoint.Delegated.Upload` app
  role; and
- service principals by the `MCP.SharePoint.Application.Read` or
  `MCP.SharePoint.Application.Upload` app role.

AgentCore exposes JWT claims as principal tags. The exact serialized form of
the Entra `roles` claim must be verified with real non-production tokens before
enforcement. The policies quote the full role value inside the serialized
array to avoid prefix matches.
