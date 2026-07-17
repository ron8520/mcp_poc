# End Goal

This document describes the target state for the enterprise MCP platform.

## Target Outcome

The target state is one governed internal AgentCore Gateway endpoint configured
for MCP for the first production slice, using the AWS-managed AgentCore Gateway
URL:

```text
https://{gateway-id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp
```

The first enabled MCP server is SharePoint. CRM, internal software, and future
systems are separate MCP servers behind the same Gateway, each with its own
container image, AgentCore Runtime, Gateway target, allowlist, and owner.
A centrally owned `mcp-python-base` image is an optional future hardening
pattern, not a current PoC dependency.

## Target Production Flow

```text
Claude Code / People Assist Lambda / internal agents
  -> obtain Entra JWT for the Enterprise MCP API
  -> send HTTPS MCP request with Authorization: Bearer <Entra JWT>
  -> AgentCore Gateway PrivateLink/default Gateway DNS where available
  -> AgentCore Gateway
  -> Gateway MCP target for the selected server
  -> AgentCore Runtime for the selected MCP server
  -> approved downstream system
```

Claude Code's MCP request is authorized by the Entra JWT, not by AWS IAM. AWS IAM
roles are used on the AWS side after ingress, including Gateway-to-Runtime
invocation, Runtime observability, secret access, and Bedrock access where the
approved model path runs on AWS infrastructure. If a developer workstation calls
Bedrock directly, that IAM credential remains separate from the MCP bearer token.

People Assist Lambda can send email directly through its approved email path.
It should call MCP only when it needs governed SharePoint tool access.

## MCP Server Targets

The first enabled target is `sharepoint-mcp`, which should provide:

- `sharepoint_list_site_content`
- `sharepoint_get_file_text`
- `sharepoint_insert_site_page_content`
- `sharepoint_update_file_content`

Write tools should require:

- explicit site allowlist
- caller allowlist
- change ticket
- idempotency key
- expected ETag or equivalent concurrency control
- structured audit metadata

Future targets:

- `crm-mcp`: disabled until CRM tool contracts are approved.
- `internal-software-mcp`: disabled until internal API tool contracts are
  approved.

## Identity Target

Inbound MCP authorization:

- Entra ID issues environment-specific tokens such as
  `api://enterprise-mcp-nonprod` and `api://enterprise-mcp-prod`.
- Entra app registrations are managed as code in the cloud-owned
  `identity/entra` Terraform root, separate from AWS AgentCore infrastructure
  state.
- Gateway validates issuer, audience, allowed client IDs, scopes, app roles, and
  groups.
- Claude Code/developer tooling obtains delegated Entra tokens.
- People Assist Lambda obtains app-only Entra tokens with client credentials.
- Gateway policy or runtime policy maps callers to allowed tools and sites.
- Entra remains the token issuer and source of caller identity. Gateway
  `CUSTOM_JWT` validation uses the managed AgentCore Identity inbound
  authorization capability; no separate AgentCore Identity credential provider
  is required for this inbound flow.
- AWS IAM roles do not replace the Entra caller JWT for MCP. IAM is used by AWS
  services after the request reaches the AWS-side Gateway/Runtime boundary.

Downstream SharePoint authorization:

- Use a separate downstream app/credential for Graph.
- Prefer selected permissions such as `Sites.Selected`.
- Do not reuse the inbound caller JWT as the Graph token.

## Infrastructure Target

Infrastructure should be deployed with Terraform through workspaces/pipelines
created by the central TFE admin repo.

Use one Terraform codebase for nonprod and prod. Both environment workspaces
should use the same `infra` working directory and set environment differences
through `nonprod.tfvars` and `prod.tfvars`.

Target resources:

- One AgentCore Runtime per enabled MCP server container.
- AgentCore Gateway with `CUSTOM_JWT`.
- One Gateway MCP target per enabled Runtime.
- Gateway semantic search enabled for tool discovery.
- Gateway role signing upstream Runtime requests.
- Runtime resource policy allowing only Gateway invocation for each Runtime.
- Runtime IAM trust policies constrained by source account and source ARN.
- Runtime observability permissions for CloudWatch Logs, metrics, and X-Ray.
- Runtime VPC mode with private subnets and restricted security groups.
- AgentCore Gateway interface VPC endpoint for private clients.
- No CloudFront or CDN-backed custom domain for this MCP path.

The central image push pipeline is out of scope because the central ECR image
platform already exists. The platform may later add a standard optional base
image contract for service images.

## Success Criteria

The platform is successful when:

- Claude Code can call MCP by sending an Entra bearer token to AgentCore Gateway.
- Any Bedrock IAM usage remains separate from the MCP caller JWT or is handled by
  AWS-hosted server roles outside the MCP authorization path.
- People Assist Lambda can optionally call MCP using an app-only Entra token.
- Terraform configures Gateway JWT trust but does not obtain Entra tokens.
- Gateway rejects callers without valid environment-specific Enterprise MCP API
  authorization.
- Gateway or runtime policy rejects unauthorized tool/site combinations.
- Tool policy is maintained in YAML, validated by JSON Schema, and generated
  into runtime JSON before deployment.
- SharePoint tools can only operate on selected approved sites.
- Write tools require a change ticket and idempotency key.
- Runtimes cannot be invoked directly except by the Gateway role.
- Clients use the AWS-managed Gateway MCP URL, with PrivateLink/private DNS
  where available.
- Each MCP server deploys to Runtime as a final service image URI. Optional base
  image adoption does not change the Terraform Runtime input.
- Nonprod and prod use the same Terraform root with separate Terraform state and
  selected `nonprod.tfvars` / `prod.tfvars` files.
- MCP server and policy changes are validated by CI/CD workflows with explicit
  Azure DevOps ownership and manual production gates.
- Policy bundle PRs are gated by a required, path-scoped Azure DevOps build
  validation policy; failed policy validation blocks merge regardless of any
  automatic TFE plan run.
- Entra client IDs and audience values are produced by the identity workspace
  and consumed by the AWS Gateway workspace.
