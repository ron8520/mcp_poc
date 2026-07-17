# In Progress

This document tracks work that is still being refined or not yet implemented.

## Architecture Validation

- Obtain accountable-owner review of the internal architecture review pack and
  close or explicitly accept every listed approval condition before production.
- Validate Gateway `protocol_type = "MCP"` with multiple `mcp_server` targets,
  each pointing at one AgentCore Runtime invocation endpoint.
- Validate Gateway semantic search with `x_amz_bedrock_agentcore_search`.
- Validate Gateway IAM signing to each Runtime with `service = "bedrock-agentcore"`.
- Validate Runtime resource policies that allow only the Gateway role.
- Validate Runtime trusted header allowlisting for sanitized caller context.
- Validate AgentCore Gateway PrivateLink and private DNS for Lambda/private
  developer networks.
- Validate MCP clients against the AWS-managed Gateway URL.

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

- Replace dry-run Graph calls with Microsoft Graph calls.
- Add downstream credential handling.
- Add selected SharePoint site permission setup.
- Add text extraction rules per file type.
- Add ETag handling for file updates.
- Add idempotency storage for writes.
- Add tests for denied tools, denied sites, and missing change tickets.

## Future MCP Server Boundaries

- Define CRM MCP tool contracts before enabling `crm-mcp`.
- Define internal software MCP tool contracts before enabling
  `internal-software-mcp`.
- Keep each downstream system in its own server folder and image.

## Optional Base Image

- Decide later whether the platform actually needs `mcp-python-base`.
- If adopted, validate the `mcp-python-base` build in the central ECR account.
- Replace example dependency files with internally mirrored, hash-pinned locks.
- Add SBOM, vulnerability scan, image signing, and compatibility gates in the
  central image pipeline if the optional base image is adopted.
- Define base image versioning and rollback policy only if adopted.

## Tool Allowlist

- Finalize Entra client IDs, app roles, and group names.
- Populate Gateway `entra_allowed_clients` with approved Claude Code and service
  app registrations.
- Decide owner/reviewer model for allowlist changes.
- Extend policy matrix tests as each new tool is enabled.
- Decide whether Gateway policy engine or Runtime policy is the primary
  enforcement point for each rule.
- Define trusted caller claim propagation if Runtime needs caller context.
- Generate or hand-author Gateway Cedar policies from the YAML policy source.

## CI/CD

- Configure the Azure DevOps Server pipelines from
  `examples/enterprise_mcp_platform/pipelines/azure-devops`.
- Add real image scanning, SBOM, signing, and central ECR publish gates.
- Connect image publish outputs to the central TFE admin repo / Terraform
  workspace change process.
- Configure the required `policy-ci.yml` Azure DevOps build validation policy
  with the documented path filter for policy bundle changes.
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

- Validate the flat Terraform root files for Runtime, Gateway, IAM, and
  PrivateLink resources.
- Validate the shared `infra` root from both nonprod and prod central TFE
  workspace runs using `nonprod.tfvars` and `prod.tfvars`.
- Pin the AWS provider version once AgentCore resources are validated.
- Wire final service image URIs as inputs per MCP server.
- Validate the VPC endpoint and PrivateLink resources in the target accounts.
- Do not add CloudFront for this MCP path.
- Do not add Cognito or separately managed AgentCore Identity outbound
  credential providers, token-vault configuration, or workload-token
  permissions unless an outbound-token brokerage requirement is approved.
