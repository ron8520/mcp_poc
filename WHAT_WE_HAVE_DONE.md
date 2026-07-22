# What We Have Done

This document captures decisions and work completed so far.

## Architecture Decisions

- Clarified that v1 should start with one shared AgentCore Gateway endpoint
  configured for MCP.
- Clarified that SharePoint is the first enabled MCP server, not the only future
  server.
- Added separate code boundaries for SharePoint, CRM, and internal software MCP
  servers.
- Clarified that People Assist does not need MCP for email sending.
- Chose AgentCore Gateway as the front door for MCP callers.
- Chose AgentCore Runtime as the hosting layer for each MCP server container.
- Chose Entra JWTs for MCP caller identity.
- Clarified that Claude Code calls MCP with an Entra bearer token and that AWS
  IAM roles are server-side for Gateway, Runtime, AWS services, and any approved
  Bedrock path.
- Chose Terraform as the infrastructure implementation path.
- Assumed central ECR already hosts internal container images.
- Added an optional MCP base-image pattern for future shared container controls.
- Rejected CloudFront/CDN-backed custom domains for the public-sector MCP path.
- Chose AWS-managed AgentCore Gateway URL plus PrivateLink/private DNS for
  private client access.
- Compared AWS AgentCore samples and adopted the useful Gateway/Runtime
  patterns while keeping Entra instead of Cognito.
- Clarified the identity boundary: Entra remains the caller-token issuer, while
  Gateway `CUSTOM_JWT` validation is the managed AgentCore Identity inbound
  authorization capability. No outbound credential provider or token vault is
  part of the approved first slice.
- Added a comprehensive internal architecture, security and migration review
  pack with editable draw.io diagrams, a STRIDE threat register, control
  requirements, phased migration gates, rollback triggers and approval conditions.

## Example Code

Added `examples/enterprise_mcp_platform` with:

- enterprise folder structure
- common runtime helpers
- SharePoint MCP server
- CRM MCP placeholder boundary
- internal software MCP placeholder boundary
- optional MCP Python base-image example
- narrow list/get/insert/update SharePoint tools
- dry-run Graph client
- policy-as-code YAML allowlist
- JSON Schema for policy format validation
- generated runtime policy JSON
- policy validation script with embedded policy test cases
- allowlist enforcement helper
- local MCP client
- Claude Code-style MCP validation client
- Gateway semantic-search smoke client
- People Assist Lambda Gateway invocation example
- Gateway interceptor example for sanitized caller context
- Flat Terraform root files for IAM, AgentCore Runtime, AgentCore Gateway,
  Gateway targets, resource policy, and PrivateLink access
- Shared Terraform root for nonprod and prod environment runs
- Windows PowerShell Entra token helper for delegated and app-only token examples
- Terraform Gateway Entra `allowed_clients` input
- Entra identity Terraform example for Enterprise MCP API, Claude Code client,
  People Assist client, app roles, and optional Conditional Access
- Runtime IAM trust conditions and observability permissions
- Runtime trusted header allowlist
- Azure DevOps MCP server CI/CD pipeline example
- Azure DevOps policy CI/CD pipeline example
- Azure DevOps policy CI branch-policy path filter guidance
- cloud-owned repo boundary documentation

## Documentation

- Updated README with the shared Gateway and separate MCP server architecture.
- Added architecture and sequence diagrams to README.
- Added an editable draw.io version of the Claude Code identity sequence and embedded its rendered PNG in the developer architecture guide.
- Reworked the generated Word report from a security approval pack into a developer-oriented wiki with repository navigation, local workflows, implementation status, verification guidance and known gaps.
- Updated ADR 0001 with the AgentCore Gateway for MCP decision.
- Added Claude Code and People Assist sequence diagrams to ADR.
- Documented the AWS-managed Gateway URL and no-CloudFront decision.
- Documented the optional base-image build sequence.
- Documented AWS sample learnings and the no-AgentCore-Identity decision.
- Documented that Terraform configures Gateway JWT trust but callers obtain
  Entra tokens at runtime.
- Added ADR 0005 for required path-scoped Azure DevOps policy PR validation.
- Documented one-codebase/two-environment Terraform model.
- Documented the flat `infra/` Terraform root with resource-focused files
  instead of nested Terraform directories.
- Added ADR 0002 for policy-as-code and DevOps workflow ownership.
- Added ADR 0003 for on-prem Azure DevOps and the cloud-owned platform repo.
- Added ADR 0004 for the Claude Code Entra JWT and AWS IAM credential boundary.
- Added DevOps workflow diagrams for MCP server CI/CD, policy CI/CD, Claude
  Code discovery authorization, fixed production agent authorization, Entra
  identity Terraform, AWS AgentCore Terraform, and repo ownership.
- Added an Entra identity configuration workflow diagram.

## Remaining Validation

- Real AgentCore Gateway-to-Runtime target behavior.
- Claude Code token/header support.
- PrivateLink/private DNS behavior for MCP clients.
- Real Microsoft Graph implementation.
- Final Entra app registration and group/app-role names.
- Approved Entra token flow for Claude Code and Lambda client credentials.
- `nonprod.tfvars` and `prod.tfvars` values for the shared Terraform roots.
- Central ECR base-image scanning, signing, SBOM, and compatibility validation.
- Gateway semantic search behavior with real Claude Code.
- Gateway Cedar policy generation from the YAML matrix.
- Real Azure DevOps variable groups, environments, approvals, image scanning,
  SBOM, and signing configuration.
- Central TFE admin repo workspace setup for `identity/entra` and `infra`.
