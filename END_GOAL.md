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

The current released MCP specification is `2025-11-25`. Python SDK
`mcp==2.0.0` targets the `2026-07-28` release candidate, but the managed
AgentCore Gateway dialect remains a non-production validation gate.

## Target Production Flow

```text
Employee-facing AI apps and MCP clients / approved background workloads
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

The MCP request is authorized by the Entra JWT, not by AWS IAM. AWS IAM roles
remain server-side for current Gateway-to-Runtime invocation, Runtime
observability, workload access to lane-scoped AgentCore Identity providers, and
Bedrock access where the approved model path runs on AWS infrastructure. The
target delegated Gateway-to-Runtime hop instead validates an Identity-brokered
Runtime-audience JWT. If a developer workstation calls Bedrock directly, that
IAM credential remains separate from the MCP bearer token.

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

An AI application is not inherently an application-identity caller. An
employee-facing AI app uses delegated identity whenever downstream user
permissions must apply. A true background workflow with no employee security
subject uses M2M. Each future server records whether it needs delegated, M2M,
both, native IAM, or no outbound credential before a lane is created.

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

This section describes the target accepted for PoC validation; it does not
describe the current repository implementation. The implemented PoC remains
Gateway `CUSTOM_JWT`, two fixed Gateway-to-Runtime IAM/SigV4 lanes, delegated
Lambda assertion-copy plus Runtime MSAL OBO, and a gated-off app-only ingress.
The repository now also contains an explicit app-only caller-context resolver,
AgentCore M2M adapter, and Terraform wiring behind that gate. Local tests and
plans do not prove a live AgentCore, Entra provider, token exchange, or Graph
grant.
The target OBO/M2M decision and non-production gates are defined in
[`docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md`](docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md).

Inbound MCP authorization:

- Entra ID issues environment-specific tokens such as
  `api://enterprise-mcp-nonprod` and `api://enterprise-mcp-prod`.
- The `deployment/` Terraform root composes the `identity/entra` and `infra`
  modules. One TFE workspace/state per environment owns the Entra API,
  app-only catalog, AgentCore Gateway, Runtime, and their wiring; `nonprod` and
  `prod` remain separate states and approval paths.
- Gateway validates issuer, audience, expiry, and allowed client IDs.
- An employee uses the approved token helper to obtain a delegated Entra token;
  Claude Code is one example, while another employee-facing AI app may use its
  own approved delegated flow.
- An approved background workflow such as People Assist Lambda obtains an
  app-only Entra token with client credentials only when no employee is the
  downstream security subject and an approved caller credential has been
  provisioned. The catalog Terraform creates the caller registration/service
  principal and role, but does not create a password, certificate or federated
  credential.
- Direct Cedar maps delegated scopes/application roles to exact MCP tools.
- Delegated and application roles represent tool capability, not SharePoint
  site membership.
- Entra remains the token issuer and source of caller identity. Gateway
  `CUSTOM_JWT` validation uses the managed AgentCore Identity inbound
  authorization capability; no separate AgentCore Identity credential provider
  is required for this inbound flow.
- AWS IAM roles do not replace the Entra caller JWT for MCP. IAM is used by AWS
  services after the request reaches the AWS-side Gateway/Runtime boundary.

Current PoC downstream authorization:

- Gateway invokes both fixed SharePoint lanes with IAM/SigV4.
- The delegated lane copies the validated inbound bearer as
  `x-mcp-user-assertion`; the Runtime performs MSAL Graph OBO.
- The application lane uses a separate Graph application identity and remains
  gated off at Gateway ingress. It uses client credentials, not OBO.
- Do not use the inbound Enterprise MCP JWT directly as a Microsoft Graph
  token.

Target delegated authorization (accepted for PoC validation):

- AgentCore Identity performs two audience-specific OBO exchanges:
  Gateway-audience token -> Runtime-audience token -> Graph-audience token.
- Gateway target authorization uses Identity `TOKEN_EXCHANGE`; the target
  delegated Runtime validates Token B rather than receiving the current PoC's
  SigV4 request plus copied Token A assertion.
- OBO is for delegated user access only. The current Lambda/MSAL path remains
  until non-production validation passes.
- Graph applies the employee's native site/item permissions.

Target app-only authorization (accepted for PoC validation):

- App-only remains Entra `client_credentials`, with one application Runtime per
  approved trust domain rather than one Runtime per caller or provider.
- The deployment input `app_only_apps[stable_workload_name]` contains an owner
  and a `grants` map of `site_id` to exact MCP tools. Each enabled entry creates
  a caller Entra application/service principal and a separate downstream
  SharePoint application/service principal. App-only roles are assigned
  directly; sensitivity groups are not used. Delegated user groups remain on
  the delegated path.
- After caller validation and provider resolution, the Runtime uses AgentCore
  Identity `M2M` to obtain the downstream application token. Long-lived OAuth
  provider credentials are not exposed to MCP code or tool input.
- A thin default-deny resolver can select among approved Identity provider
  profiles in that domain. Its platform key is validated caller client ID,
  exact target-qualified action, server-owned downstream resource key, and
  environment. SharePoint keeps the existing `site_id` unchanged.
- The caller cannot supply authentication mode, provider alias, ARN, client ID,
  secret, or a `resource_ref`. Misses, mismatches, unavailable configuration,
  and provider failures fail closed without provider disclosure.
- The PoC adapter uses `GRAPH_AUTH_MODE=agentcore_m2m`, calls
  `GetWorkloadAccessToken(workloadName)` and `GetResourceOauth2Token` with
  `oauth2Flow=M2M`, and requests a downstream token per Graph call. The bounded
  `APP_ONLY_MAPPING_JSON` Runtime environment value is capped at 5000
  characters. The interim `app_only_provider_bindings` input names already
  registered provider ARNs; provider registration and its credential method are
  unresolved. Caller application credential provisioning is also unresolved;
  Entra/AD synchronization does not create that credential.
- The preferred PoC caller-context gate copies the original signed caller JWT
  to `x-mcp-caller-assertion` without token exchange or secret lookup. The
  Runtime accepts only Gateway SigV4 ingress and revalidates `iss`, Gateway
  `aud`, `exp`, `tid`, v2 `azp` or v1 `appid`, and `roles`. Native no-code
  composition and `JWT_PASSTHROUGH` are not accepted defaults until validated.
- Graph applies explicit `Sites.Selected` grants.

Target lane isolation:

- The delegated Runtime/workload identity may access only approved OBO provider
  ARNs; the application Runtime/workload identity may access only approved M2M
  provider ARNs.
- A shared Runtime IAM role has the union of the provider ARNs in its approved
  trust domain. This is logical per-workload routing, not per-app hard
  isolation; use a separate Runtime/IAM boundary when that stronger isolation
  is required.
- A caller cannot switch lanes through a tool argument. Delegated tokens are
  denied from M2M targets/actions and application tokens are denied from
  delegated targets/actions.
- AgentCore Identity brokers tokens; the downstream API still makes the final
  user-ACL or application-grant decision.

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
should use the same `deployment` working directory, which composes
`module.entra` and `module.platform`, and set environment differences through
`nonprod.tfvars` and `prod.tfvars`.

Target resources:

- Direct Gateway MCP server targets for approved vendor-operated endpoints.
- An enterprise-hosted Terraform MCP Runtime/target restricted to the public
  Registry toolset.
- The current PoC retains separate delegated and application SharePoint Runtime
  lanes, built from the same service source/image, while identity target gates
  are validated.
- The target app-only deployment creates one application Runtime for each
  approved trust domain, not per caller/provider and not a universal
  all-provider Runtime. New Runtimes are normally needed only for a new trust
  domain or isolation boundary.
- Each trust-domain Runtime may select multiple provider profiles through its
  thin resolver, while every AgentCore Identity provider ARN is constrained by
  trust-domain IAM. Delegated and application workloads have non-overlapping
  OBO and M2M provider allowlists.
- The reviewed Terraform deployment input is the source of truth for the small,
  immutable app-only catalog and provider-binding map. The first Runtime
  delivery is the bounded `APP_ONLY_MAPPING_JSON` environment value (maximum
  5000 characters); there is no dynamic configuration service or generic policy
  engine. A pinned private S3 snapshot may be evaluated if BAU size requires it;
  AgentCore Configuration Bundle delivery is optional and deferred.
- Runtime cache, rollback, kill switch, drift detection, and audit evidence are
  required before enabling target routing. The default OAuth provider quota is
  50 per account/region and must be confirmed or adjusted through the AWS quota
  process.
- AgentCore Gateway with `CUSTOM_JWT`.
- One Gateway target per enabled remote endpoint or Runtime lane.
- Gateway semantic search enabled for tool discovery.
- Deliberate target synchronization after vendor capability review; discovered
  capabilities do not bypass Cedar.
- Gateway role signing current and target application Runtime requests; target
  delegated Runtime requests use the Identity-brokered Runtime-audience JWT.
- Current/application Runtime resource policies allowing only Gateway IAM
  invocation; target delegated Runtime JWT authorization allows only the
  approved Runtime audience/client path from its Gateway target.
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
- People Assist Lambda can call MCP using an app-only Entra token only after the
  app-only ingress and caller-context validation gates pass.
- An employee-facing AI application that requires downstream user authorization
  can call only the delegated lane with the employee security subject preserved;
  it cannot select the M2M lane or an application provider through MCP input.
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
- The current PoC OBO assertion header reaches only the SharePoint delegated
  target/Runtime and is absent from application lanes.
- The target delegated path proves the two audience-specific OBO exchanges in
  non-production before replacing the current Lambda/MSAL path.
- The target app-only path proves AgentCore Identity M2M, Gateway/Cedar caller
  and exact input policy, Runtime resolver safety/credential routing, and Graph
  `Sites.Selected` final authorization as separate layers.
- Each approved app-only workload has a stable owner, separate caller and
  downstream app/service principals, and exact site-to-tool grants with no
  sensitivity-group dependency. Terraform performs Graph `Sites.Selected`
  admin consent for the downstream app; the explicit per-site grant remains a
  separate downstream-owner/admin operation and is published as a handoff.
- Runtime/workload IAM proves cross-lane, cross-server, wildcard, and cross-
  trust-domain Identity provider access is denied.
- Onboarding follows disabled -> create/update catalog identities and grants ->
  validate -> enable. Revoke ingress/native grants before invalidating or
  waiting out old sessions and tokens; code rollback and permission rollback
  remain separate operations.
- Tool policy is maintained directly as Cedar and validated by AgentCore
  against the live Gateway schema with `FAIL_ON_ANY_FINDINGS`.
- Employee site access follows native SharePoint ACLs; application site access
  follows explicit `Sites.Selected` grants.
- The SharePoint upload tool accepts only `site_id`, `file_path`, and `content`
  from the caller, preserves valid values, and fails immediately on invalid
  input.
- Current and target application Runtimes cannot be invoked directly except by
  the Gateway role; the target delegated Runtime accepts only the approved
  Runtime-audience JWT path from its Gateway target.
- Clients use the AWS-managed Gateway MCP URL, with PrivateLink/private DNS
  where available.
- Each platform-owned or enterprise-hosted MCP server deploys to Runtime as a
  final service image URI. Optional base-image adoption does not change the
  Terraform Runtime input.
- Nonprod and prod use the same composed deployment root with one TFE workspace
  and state per environment, selected `nonprod.tfvars` / `prod.tfvars` files,
  and independently reviewed outputs.
- MCP server and direct Cedar changes are validated by CI/CD workflows with explicit
  Azure DevOps ownership and manual production gates.
- Direct Cedar PRs are gated by a required, path-scoped Azure DevOps build
  validation policy; failed policy validation blocks merge regardless of any
  automatic TFE plan run.
- Entra client IDs and audience values are produced by `module.entra` and wired
  directly into `module.platform` by the composed deployment workspace.
