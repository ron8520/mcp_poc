# End Goal

This document describes the target state for the enterprise MCP platform.

## Target Outcome

The target state is one governed internal AgentCore Gateway endpoint configured
for MCP for the first production slice, using the AWS-managed AgentCore Gateway
URL:

```text
https://{gateway-id}.gateway.bedrock-agentcore.{region}.amazonaws.com/mcp
```

The first enabled business-system integration is SharePoint. AWS Knowledge,
Microsoft Learn, and a Registry-only Terraform MCP Runtime are the first
documentation-target PoC. Platform-owned servers keep separate source/image,
Runtime, Cedar, and ownership boundaries; compatible vendor-operated remote MCP
endpoints may be direct Gateway targets. A centrally owned `mcp-python-base`
image is an optional future hardening pattern, not a current PoC dependency.

## Target Production Flow

```text
Claude Code / People Assist Lambda / internal agents
  -> obtain Entra JWT for the Enterprise MCP API
  -> send HTTPS MCP request with Authorization: Bearer <Entra JWT>
  -> externally managed AgentCore Gateway PrivateLink/default Gateway DNS
     where available
  -> AgentCore Gateway
  -> direct Cedar authorization for the exact target-qualified tool
  -> direct AWS Knowledge or Microsoft Learn remote target
     OR Registry-only Terraform MCP Runtime
     OR SharePoint delegated/application Runtime lane
  -> approved downstream system
```

Claude Code's MCP request is authorized by the Entra JWT, not by AWS IAM. AWS IAM
roles are used on the AWS side after ingress, including Gateway-to-Runtime
invocation, Runtime observability, secret access, and Bedrock access where the
approved model path runs on AWS infrastructure. If a developer workstation calls
Bedrock directly, that IAM credential remains separate from the MCP bearer token.

People Assist Lambda can send email directly through its approved email path.
It should call MCP only when it needs governed SharePoint tool access.

For infrastructure development, Claude Code uses approved documentation tools
through Gateway, creates or updates Terraform in the local repository, and
pushes through standard Azure DevOps Server Git/PR controls. The existing
Azure DevOps-to-TFE workflow triggers plan and approved apply. Neither Gateway
nor the Terraform MCP server pushes code or executes Terraform.

## MCP Server Targets

The first enabled service is SharePoint. It is exposed through separate
`sharepoint-delegated` and `sharepoint-application` targets/Runtimes built from the
same SharePoint MCP source and image. Both lanes should provide:

- `sharepoint_list_site_content`
- `sharepoint_get_file_text`
- `sharepoint_upload_file(site_id, file_path, content)`

The upload contract should:

- authorize the exact lane-qualified tool in Cedar;
- upload UTF-8 content to the supplied path in the site's default document
  library;
- raise an error for invalid required input; and
- preserve accepted input exactly rather than trimming, normalizing, repairing,
  or replacing it.

An empty `content` string is valid and creates an empty file.

Future targets:

- `crm-mcp`: disabled until CRM tool contracts are approved; begin with one
  application lane unless the CRM API requires delegated user semantics.
- `internal-software-mcp`: disabled until internal API tool contracts are
  approved.

Documentation targets:

- `aws-knowledge`: direct remote MCP target for public AWS technical content.
- `microsoft-learn`: direct remote MCP target for public Microsoft Learn
  documentation and code samples.
- `terraform-registry`: enterprise-hosted HashiCorp Terraform MCP Runtime with
  only `--toolsets=registry`, `ENABLE_TF_OPERATIONS=false`, and no TFE
  credential.

Public documentation targets must not receive secrets, customer records,
private source code, or sensitive document content. Newly synchronized tools
remain unusable until direct Cedar explicitly authorizes the target-qualified
action.

Databricks data access remains a separate future decision because its OAuth,
Unity Catalog, preview lifecycle, and data-egress controls are not approved by
ADR 0009.

## Identity Target

Inbound MCP authorization:

- Entra ID issues environment-specific tokens such as
  `api://enterprise-mcp-nonprod` and `api://enterprise-mcp-prod`.
- Entra app registrations are managed as code in the cloud-owned
  `identity/entra` Terraform root, separate from AWS AgentCore infrastructure
  state.
- Gateway validates issuer, audience, expiry, and allowed client IDs.
- An employee uses the approved token helper to obtain a delegated Entra token;
  Claude Code only reads `ENTRA_ACCESS_TOKEN` and sends it to Gateway.
- People Assist Lambda obtains app-only Entra tokens with client credentials.
- Direct Cedar maps delegated scopes/application roles to exact MCP tools.
- Delegated and application roles represent tool capability, not SharePoint
  site membership.
- Entra remains the token issuer and source of caller identity. Gateway
  `CUSTOM_JWT` validation uses the managed AgentCore Identity inbound
  authorization capability; no separate AgentCore Identity credential provider
  is required for this inbound flow.
- AWS IAM roles do not replace the Entra caller JWT for MCP. IAM is used by AWS
  services after the request reaches the AWS-side Gateway/Runtime boundary.

Downstream SharePoint authorization:

- The delegated Runtime performs Graph OBO and SharePoint applies the
  employee's native site/item permissions.
- Gateway invokes the delegated Runtime with SigV4 and a trusted
  interceptor-provided assertion header; the assertion is never accepted as an
  MCP tool argument.
- The application Runtime uses a separate Graph application identity limited
  by explicit `Sites.Selected` grants.
- Do not use the inbound Enterprise MCP JWT directly as a Microsoft Graph
  token.

## Infrastructure Target

Infrastructure should be deployed with Terraform through workspaces/pipelines
created by the central TFE admin repo.

The workload root deploys AgentCore Gateway/Runtime in Sydney
(`ap-southeast-2`). Melbourne (`ap-southeast-4`) is a future candidate that
must remain disabled until AWS publishes the required AgentCore endpoints and
VPC support and the platform team validates them. The central platform/TFE
configuration supplies the target AWS account ID and the existing Runtime
subnet/security-group IDs.

Use one Terraform codebase for nonprod and prod. Both environment workspaces
should use the same `infra` working directory and set environment differences
through `nonprod.tfvars` and `prod.tfvars`.

Target resources:

- Direct Gateway MCP server targets for approved vendor-operated endpoints.
- An enterprise-hosted Terraform MCP Runtime/target restricted to the public
  Registry toolset.
- Separate delegated and application Runtime deployments for SharePoint, built
  from the same service source/image.
- Runtime lanes are created per downstream credential mode, not as a universal
  two-Runtime rule for every future MCP server.
- AgentCore Gateway with `CUSTOM_JWT`.
- One Gateway target per enabled remote endpoint or Runtime lane.
- Gateway semantic search enabled for tool discovery.
- Deliberate target synchronization after vendor capability review; discovered
  capabilities do not bypass Cedar.
- Gateway role signing upstream Runtime requests.
- Runtime resource policy allowing only Gateway invocation for each Runtime.
- Runtime IAM trust policies constrained by source account and source ARN.
- Runtime observability permissions for CloudWatch Logs, metrics, and X-Ray.
- Runtime VPC mode with private subnets and restricted security groups.
- Existing AgentCore Gateway interface VPC endpoint for private clients,
  managed by the network/platform account outside this workload root.
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
- Direct Cedar at Gateway rejects unauthorized caller/tool/input combinations.
- Gateway can route to an approved vendor-operated remote MCP endpoint without
  an unnecessary Runtime proxy.
- AWS Knowledge and Microsoft Learn expose only reviewed public-documentation
  tools.
- The Terraform MCP Runtime exposes only the public Registry toolset, has
  Terraform operations disabled, and has no TFE credential.
- A newly synchronized vendor tool remains denied until an explicit Cedar
  change is reviewed and deployed.
- Documentation queries and logs contain no secrets, private source code,
  customer records, tokens, or full retrieved documents.
- Claude Code writes Terraform locally; Git/PR and TFE remain the only approved
  code-delivery and deployment path.
- The OBO assertion header reaches only the SharePoint delegated target/Runtime
  and is absent from application lanes.
- Tool policy is maintained directly as Cedar and validated by AgentCore
  against the live Gateway schema with `FAIL_ON_ANY_FINDINGS`.
- Employee site access follows native SharePoint ACLs; application site access
  follows explicit `Sites.Selected` grants.
- The SharePoint upload tool accepts only `site_id`, `file_path`, and `content`
  from the caller, preserves valid values, and fails immediately on invalid
  input.
- Runtimes cannot be invoked directly except by the Gateway role.
- Clients use the AWS-managed Gateway MCP URL, with PrivateLink/private DNS
  where available.
- Each platform-owned or enterprise-hosted MCP server deploys to Runtime as a
  final service image URI. Optional base-image adoption does not change the
  Terraform Runtime input.
- Nonprod and prod use the same Terraform root with separate Terraform state and
  selected `nonprod.tfvars` / `prod.tfvars` files.
- MCP server and direct Cedar changes are validated by CI/CD workflows with explicit
  Azure DevOps ownership and manual production gates.
- Direct Cedar PRs are gated by a required, path-scoped Azure DevOps build
  validation policy; failed policy validation blocks merge regardless of any
  automatic TFE plan run.
- Entra client IDs and audience values are produced by the identity workspace
  and consumed by the AWS Gateway workspace.
