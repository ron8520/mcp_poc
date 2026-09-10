# In Progress

This document tracks work that is still being refined or not yet implemented.

## Architecture Validation

- Complete architecture, security, identity and data-owner production-readiness
  review, then resolve or explicitly accept every open risk before production.
- Validate Gateway `protocol_type = "MCP"` with both vendor-operated remote MCP
  targets and AgentCore Runtime-hosted targets.
- Validate Gateway semantic search with `x_amz_bedrock_agentcore_search`.
- Validate current-PoC Gateway IAM signing to each Runtime with
  `service = "bedrock-agentcore"` and current Runtime resource policies that
  allow only the Gateway role.
- Separately validate target delegated Gateway `TOKEN_EXCHANGE`, Runtime-
  audience JWT authorization, and direct-client denial.
- Validate Runtime header allowlisting for correlation metadata plus the
  interceptor-owned OBO assertion on the delegated lane only.
- Validate the network/platform account's existing AgentCore Gateway
  PrivateLink, private DNS, endpoint policy, and routing for Lambda/private
  developer networks.
- Validate MCP clients against the AWS-managed Gateway URL.
- Keep SDK 2 Gateway clients in `mode="legacy"`; `2025-11-25` is the current
  released MCP specification, while `2026-07-28` is an RC/target. Validate the
  managed AgentCore Gateway dialect before claiming support for the RC.

## Identity Routing PoC Gates

The current repository implementation is the baseline while these target gates
are open:

- Keep Gateway `CUSTOM_JWT`, two fixed Gateway-to-Runtime IAM/SigV4 lanes, the
  delegated-only `x-mcp-user-assertion` interceptor, delegated Runtime MSAL OBO,
  and application Runtime client credentials unchanged during migration
  validation. The staged app-only adapter and mapping path is additive and
  remains behind the ingress gate.
- Keep app-only Gateway ingress gated off until the catalog, provider binding,
  downstream site grant, Cedar `ENFORCE`, and live token gates pass. The PoC
  `agentcore_m2m` adapter, trusted caller header, exact resolver checks, and
  `APP_ONLY_MAPPING_JSON` wiring exist, but they do not prove a deployed
  AgentCore Identity provider or live exchange.
- Validate the target delegated flow as two audience-specific OBO exchanges:
  Gateway audience -> Runtime audience -> Graph audience. OBO is delegated-user
  only; replace Lambda/MSAL only after non-production success and negative tests.
- Validate AgentCore Identity as the target broker for both lane types: OBO for
  delegated calls and `M2M` client credentials for autonomous application calls.
  Prove that Runtime code and MCP input never receive long-lived provider
  secrets.
- Prove lane selection follows the downstream security subject rather than the
  client product: an employee-facing AI app uses delegated/OBO when user ACLs
  must apply, while only a workflow with no employee subject uses M2M.
- Deny delegated tokens from M2M target/actions and application tokens from
  delegated target/actions. Reject every caller-supplied auth mode, provider,
  ARN, client ID, secret, or hidden credential-selection field.
- Validate the preferred app-only request-interceptor gate: copy the original
  signed caller JWT to `x-mcp-caller-assertion` without token exchange, secret
  lookup, or provider selection. The Runtime must accept only Gateway SigV4
  ingress and revalidate `iss`, Gateway `aud`, `exp`, `tid`, v2 `azp` or v1
  `appid`, and `roles`.
- Confirm native no-code app-only caller-context composition from official AWS
  documentation and non-production evidence; it is not currently verified.
  Keep `JWT_PASSTHROUGH` out of the default because its token
  audience/direct-Runtime implications change the Gateway policy risk model.
- Validate one application Runtime per approved trust domain, not per caller or
  provider and not a universal all-provider Runtime. Reuse one immutable image;
  create a Runtime only for a new trust-domain isolation boundary.
- Validate the thin default-deny resolver platform key: validated caller client
  ID, exact target-qualified action, server-owned downstream resource key, and
  environment. For SharePoint, keep the existing `site_id` unchanged. Callers
  cannot provide auth mode/provider/ARN/client ID/secret; miss, mismatch,
  unavailable config, or provider failure must fail closed without provider
  disclosure.
- Validate the authorization layers separately: Gateway/Cedar caller and exact
  tool/input, Runtime resolver safety and credential routing, and Graph ACL or
  `Sites.Selected` final authorization. Runtime IAM may reach only provider ARNs
  inside its trust domain.
- Validate the stable `app_only_apps` catalog: owner, separate caller and
  downstream SharePoint app/service principals, direct app-only role grants,
  and exact `site_id -> tool` entries. Do not add sensitivity groups to the
  app-only path; delegated user groups remain separate.
- Define and implement the approved authentication method for each caller
  application. The catalog creates registrations, service principals and roles
  only; it does not create a caller password, certificate or federated
  credential. Entra/AD synchronization is an identity source, not credential
  provisioning.
- Prove delegated workload IAM can reach only approved OBO providers and
  application workload IAM can reach only approved M2M providers. Add negative
  tests for wildcard, cross-lane, cross-server, and cross-domain provider access.
- Validate the reviewed Terraform input as the source of truth for the small
  immutable catalog and the explicit `app_only_provider_bindings` map. Runtime
  delivery uses `APP_ONLY_MAPPING_JSON`, capped at 5000 characters; do not add a
  dynamic configuration service, generic policy engine, or weighted/A-B
  security mapping. A pinned private S3 snapshot may be evaluated later;
  Configuration Bundle delivery is optional and deferred.
- Confirm the default OAuth provider quota of 50 per account/region (or a
  documented approved quota adjustment), and count identities by audit/isolation
  boundary rather than caller count.
- Validate onboarding/BAU gates: caller app role, Cedar rule, resolver mapping,
  reviewed config version, non-production negative tests, and production
  promotion. The operating sequence is disabled -> create/update identities
  and native grants -> validate -> enable. Revoke ingress and native grants
  before invalidating or waiting out old sessions/tokens; code rollback and
  permission rollback are separate operations. Create a Graph app/provider only
  for a distinct downstream identity, permission or audit boundary, and a
  Runtime only when that provider requires a new trust domain.

## Claude Code Validation

- Confirm how Claude Code will pass the Entra access token to the MCP endpoint.
- Confirm whether native streamable HTTP MCP with headers is enough.
- If not, test a secure local token helper/proxy.
- Confirm the approved delegated token flow: device code, auth code with local
  callback, or enterprise token helper.
- Confirm whether `enable_device_code_flow` is acceptable or whether the
  enterprise token helper must use auth-code-with-PKCE.
- Validate `clients/entra_token_helper.ps1` on a managed Windows workstation
  with the enterprise execution policy and approved Entra client registration.
- Keep AWS IAM role usage off the inbound MCP caller path. IAM should remain
  server-side for Gateway/Runtime and any approved Bedrock path.
- Correlate Bedrock and MCP audit logs with `correlation_id`.

## People Assist Validation

- Decide whether People Assist Lambda needs MCP for SharePoint reads.
- Keep email sending inside Lambda or the approved email path.
- If Lambda calls MCP, use app-only Entra token for the Gateway.
- If People Assist becomes employee-facing or performs an operation whose
  authorization must follow a signed-in employee, use the delegated lane
  instead; application code does not make the request app-only by itself.
- Confirm Lambda secret source for Entra client credentials.
- Avoid a second IAM-authorized Gateway unless there is a strong operational
  reason.

## SharePoint MCP Implementation

- Validate the real Microsoft Graph upload call against a non-production site's
  default document library.
- Validate the implemented list/read Graph branches against a real
  non-production site, including pagination, recursive listing, PDF extraction,
  the 25 MiB and 250-page input limits, output truncation, throttling and
  permission errors.
- Validate the current MSAL OBO and client-credentials handlers with real Entra
  applications and Secrets Manager values; this does not prove native target
  AgentCore Identity OBO or M2M.
- Validate the staged Runtime AgentCore Identity `M2M` adapter against the
  approved Graph provider and prove an ungranted SharePoint site remains denied;
  the provider registration credential method remains unresolved.
- Add selected SharePoint site permission setup.
- Prove accepted `site_id`, `file_path`, and `content` values reach Graph
  unchanged.
- Add tests that missing or invalid upload inputs fail immediately without
  trimming, normalization, repair, or fallback values; keep empty `content`
  valid for an empty file.
- Add end-to-end tests for Cedar tool denial, delegated SharePoint ACL denial,
  and application `Sites.Selected` denial.

## Future MCP Server Boundaries

- Define CRM MCP tool contracts before enabling `crm-mcp`.
- Define internal software MCP tool contracts before enabling
  `internal-software-mcp`.
- Keep each downstream system in its own server folder and image.
- For every new downstream server, record whether its security subject requires
  delegated/OBO, autonomous M2M, both, AWS-native IAM, or no outbound credential.
  Do not create two lanes by default and do not infer M2M from the words "AI
  application" or "background" alone.
- Decide Databricks managed-MCP readiness, OAuth U2M/M2M lanes, Unity Catalog
  enforcement, network path, and preview-lifecycle acceptance in a separate ADR
  before enabling any Databricks data target.

## Vendor-Native and Documentation MCP Targets

- Validate direct Gateway initialization, `tools/list`, invocation, and
  synchronization for AWS Knowledge and Microsoft Learn.
- Confirm supported MCP protocol versions, availability, rate limits, terms,
  timeout behavior, and target-level kill switches.
- Define the approved Cedar action list for each public documentation target;
  prove a newly synchronized vendor tool remains denied before policy review.
- Apply data-classification controls so public documentation queries cannot
  contain secrets, tokens, customer records, private source code, or sensitive
  documents.
- Verify logs retain caller/target/tool/decision/result metadata without query
  bodies or retrieved documentation.
- Deploy and validate the HashiCorp Terraform MCP server on AgentCore Runtime
  with only `--toolsets=registry`, `ENABLE_TF_OPERATIONS=false`, and no
  `TFE_TOKEN`.
- Prove the Terraform MCP target cannot access private registries, create or
  modify TFE workspaces/runs, execute Terraform, push Git changes, or bypass the
  Azure DevOps/TFE delivery path.

## Optional Base Image

- Decide later whether the platform actually needs `mcp-python-base`.
- If adopted, validate the `mcp-python-base` build in the central ECR account.
- Replace example dependency files with internally mirrored, hash-pinned locks.
- Add SBOM, vulnerability scan, image signing, and compatibility gates in the
  central image pipeline if the optional base image is adopted.
- Define base image versioning and rollback policy only if adopted.

## Direct Cedar Authorization

- Finalize Entra client IDs, app roles, and group names.
- Populate Gateway `entra_allowed_clients` with approved Claude Code and service
  app registrations.
- Finalize the owner/reviewer model for direct Cedar changes.
- Validate the wired `aws_bedrockagentcore_policy` resources and
  `FAIL_ON_ANY_FINDINGS` behavior against the live Gateway schema.
- Keep the current Gateway-wide `mcp.invoke` scope gate until direct Cedar is
  ready for `ENFORCE`; remove it atomically with the app-only lane cutover.
- Validate the exact AgentCore principal-tag serialization for Entra `scp` and
  `roles` claims.
- Add positive and negative live Gateway tests for both credential lanes.
- Promote non-production from `LOG_ONLY` to `ENFORCE` only after denial
  evidence is accepted.

## CI/CD

- Configure the Azure DevOps Server pipelines from
  `examples/enterprise_mcp_platform/pipelines/azure-devops`.
- Add real image scanning, SBOM, signing, and central ECR publish gates.
- Connect image publish outputs to the central TFE admin repo / Terraform
  workspace change process.
- Configure the required `policy-ci.yml` Azure DevOps build validation policy
  with the documented path filter for direct Cedar changes.
- Add Azure DevOps branch policies and path-based required reviewers for
  identity, infra, server, and pipeline changes.
- Configure Azure DevOps secure variable groups and approvals for image publish.

## Entra Identity

- Validate the `identity/entra` Terraform in the enterprise tenant.
- Validate the composed `deployment/` root as the single TFE execution path for
  each environment; retain `identity/entra` as the Entra module boundary.
- Confirm Conditional Access trusted named locations and enforcement timeline.
- Confirm whether People Assist client credentials are created outside
  Terraform state.
- Confirm real app role and group object IDs for nonprod and prod.

## Terraform

- Validate the current configured `sharepoint-delegated` and fixed
  `sharepoint-application` Runtime/target deployments with the same immutable
  SharePoint image. Validate the opt-in app-only binding path separately; keep
  app-only ingress gated.
- Extend the workload Terraform only after the ADR 0009 PoC proves the selected
  external MCP target configuration and Registry-only Terraform Runtime shape.
- Validate current Gateway interceptor assertion propagation and prove the
  delegated header is absent from the application lane; separately validate the
  target `x-mcp-caller-assertion` gate before enabling app-only ingress.
- Validate the flat Terraform root files for Runtime, Gateway, IAM, and direct
  Cedar while consuming platform-provided account and Runtime network inputs.
- Validate the composed `deployment/` root from both nonprod and prod central
  TFE workspace runs using `nonprod.tfvars` and `prod.tfvars`; each environment
  has one workspace/state composing `module.entra` and `module.platform`.
- Reassess the pinned AWS provider after the first target-account validation.
- Reassess Melbourne (`ap-southeast-4`) only after AWS publishes AgentCore
  Gateway/Runtime endpoints and VPC support there; then validate it in nonprod
  before changing the regional allowlist.
- Wire final service image URIs as inputs per MCP server.
- Validate the externally managed VPC endpoint and PrivateLink path from the
  network/platform account to each target environment.
- Do not add CloudFront for this MCP path.
- Do not add Cognito or separately managed outbound token-vault behavior to the
  current PoC. Validate target AgentCore Identity OBO and M2M providers only
  through the ADR 0012 non-production gates and lane-scoped workload-token
  permissions.
