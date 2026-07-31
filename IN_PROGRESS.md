# In Progress

This document tracks work that is still being refined or not yet implemented.

## Architecture Validation

- Complete architecture, security, identity and data-owner production-readiness
  review, then resolve or explicitly accept every open risk before production.
- Validate Gateway `protocol_type = "MCP"` with both vendor-operated remote MCP
  targets and AgentCore Runtime-hosted targets.
- Validate Gateway semantic search with `x_amz_bedrock_agentcore_search`.
- Validate Gateway IAM signing to each Runtime with `service = "bedrock-agentcore"`.
- Validate Runtime resource policies that allow only the Gateway role.
- Validate Runtime header allowlisting for correlation metadata plus the
  interceptor-owned OBO assertion on the delegated lane only.
- Validate the network/platform account's existing AgentCore Gateway
  PrivateLink, private DNS, endpoint policy, and routing for Lambda/private
  developer networks.
- Validate MCP clients against the AWS-managed Gateway URL.
- Keep SDK 2 Gateway clients in `mode="legacy"` and the Gateway on its supported
  2025 protocol versions until AWS publishes and non-production testing proves
  AgentCore Gateway and Runtime support for MCP `2026-07-28`.

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
- Confirm Lambda secret source for Entra client credentials.
- Avoid a second IAM-authorized Gateway unless there is a strong operational
  reason.

## SharePoint MCP Implementation

- Validate the real Microsoft Graph upload call against a non-production site's
  default document library.
- Implement and validate the existing list/read tools' live Microsoft Graph
  branches, including bounded text extraction.
- Validate the implemented OBO and client-credentials token handlers with real
  Entra applications and Secrets Manager values.
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
- Confirm Conditional Access trusted named locations and enforcement timeline.
- Confirm whether People Assist client credentials are created outside
  Terraform state.
- Confirm real app role and group object IDs for nonprod and prod.

## Terraform

- Validate the configured `sharepoint-delegated` and `sharepoint-application`
  Runtime/target deployments with the same immutable SharePoint image.
- Extend the workload Terraform only after the ADR 0009 PoC proves the selected
  external MCP target configuration and Registry-only Terraform Runtime shape.
- Validate the Gateway interceptor assertion propagation and prove the header
  is absent from the application lane.
- Validate the flat Terraform root files for Runtime, Gateway, IAM, and direct
  Cedar while consuming platform-provided account and Runtime network inputs.
- Validate the shared `infra` root from both nonprod and prod central TFE
  workspace runs using `nonprod.tfvars` and `prod.tfvars`.
- Reassess the pinned AWS provider after the first target-account validation.
- Reassess Melbourne (`ap-southeast-4`) only after AWS publishes AgentCore
  Gateway/Runtime endpoints and VPC support there; then validate it in nonprod
  before changing the regional allowlist.
- Wire final service image URIs as inputs per MCP server.
- Validate the externally managed VPC endpoint and PrivateLink path from the
  network/platform account to each target environment.
- Do not add CloudFront for this MCP path.
- Do not add Cognito or separately managed AgentCore Identity outbound
  credential providers, token-vault configuration, or workload-token
  permissions unless an outbound-token brokerage requirement is approved.
