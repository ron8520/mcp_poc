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
- Chose AgentCore Runtime for platform-owned and enterprise-hosted MCP server
  containers; approved vendor-operated remote MCP endpoints may instead be
  direct Gateway targets.
- Chose Entra JWTs for MCP caller identity.
- Clarified that the employee obtains the Entra bearer token through
  `entra_token_helper.ps1 delegated`, Claude Code only reads and sends
  `ENTRA_ACCESS_TOKEN`, and AWS IAM roles are server-side for Gateway, Runtime,
  AWS services, and any approved Bedrock path.
- Chose Terraform as the infrastructure implementation path.
- Assumed central ECR already hosts internal container images.
- Added an optional MCP base-image pattern for future shared container controls.
- Chose direct AgentCore Cedar as the only MCP caller/tool authorization source.
- Removed the intermediate YAML, schema, generated JSON, and Runtime policy
  evaluation chain.
- Chose separate SharePoint delegated/OBO and application/app-only execution
  lanes behind the shared Gateway.
- Chose identity lanes by downstream credential mode: SharePoint needs two;
  CRM starts with one application lane unless delegated CRM semantics are
  approved.
- Kept employee site access in native SharePoint ACLs and application site
  access in explicit `Sites.Selected` grants.
- Rejected CloudFront/CDN-backed custom domains for the public-sector MCP path.
- Chose AWS-managed AgentCore Gateway URL plus PrivateLink/private DNS for
  private client access.
- Set Sydney (`ap-southeast-2`) as the current AgentCore Gateway/Runtime
  deployment region and fail closed until Melbourne (`ap-southeast-4`) has
  official endpoint and VPC support.
- Defined the target AWS account ID and existing Runtime network IDs as central
  platform/TFE inputs instead of Terraform data-source discovery.
- Assigned Gateway PrivateLink, private DNS, endpoint policy, and routing to
  the external network/platform account rather than the workload Terraform root.
- Compared AWS AgentCore samples and adopted the useful Gateway/Runtime
  patterns while keeping Entra instead of Cognito.
- Clarified the identity boundary: Entra remains the caller-token issuer, while
  Gateway `CUSTOM_JWT` validation is the managed AgentCore Identity inbound
  authorization capability. No outbound credential provider or token vault is
  part of the approved first slice.
- Chose AWS Knowledge and Microsoft Learn as direct, public
  documentation-only Gateway target candidates.
- Chose an enterprise-hosted HashiCorp Terraform MCP Runtime restricted to the
  public `registry` toolset, with Terraform operations disabled and no TFE
  credential.
- Kept Terraform code creation in Claude Code and deployment in the existing
  local Git -> Azure DevOps Server -> central TFE path.
- Deferred Databricks data access and Azure DevOps work-management operations
  to separate downstream identity decisions.
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
- narrow list/read tools plus one `sharepoint_upload_file` write tool
- dry-run Graph client
- direct Cedar policies for delegated users and application service principals
- Cedar conditions for the exact lane-qualified upload tool
- fail-fast Runtime input validation without silent cleanup or a second
  authorization engine
- local MCP client
- Claude Code-style MCP validation client
- Gateway semantic-search smoke client
- People Assist Lambda Gateway invocation example
- Gateway request interceptor that propagates the validated bearer assertion
  only to `sharepoint-delegated` calls
- Flat Terraform root files for IAM, AgentCore Runtime, AgentCore Gateway,
  Gateway targets, resource policy, and externally supplied platform inputs
- Terraform expansion from one service image into lane-specific Runtimes and
  Gateway targets
- Direct `aws_bedrockagentcore_policy` resources with
  `FAIL_ON_ANY_FINDINGS`
- Gateway execution-role permissions for Cedar evaluation
- Lane-scoped Secrets Manager access and guarded app-only ingress cutover
- MSAL Graph OBO and client-credentials token providers
- Python MCP SDK 2.0 `MCPServer` implementations for SharePoint, CRM, and
  internal software, with modern direct validation and legacy AgentCore
  Gateway client compatibility
- Python 3.13 slim as the common runtime baseline for the shared MCP base image
  and all three service images
- Shared Terraform root for nonprod and prod environment runs
- Windows PowerShell Entra token helper for delegated and app-only token examples
- Terraform Gateway Entra `allowed_clients` input
- Entra identity Terraform example for Enterprise MCP API, Claude Code client,
  People Assist client, app roles, and optional Conditional Access
- Runtime IAM trust conditions and observability permissions
- Runtime request metadata allowlist
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
- Added ADR 0006 for direct Cedar and dual SharePoint identity lanes.
- Added ADR 0007 for conditional identity lanes and the CRM deployment rule.
- Added ADR 0008 for external account/network prerequisites and Australian
  region selection.
- Added ADR 0009 for direct vendor-operated MCP targets and the restricted
  documentation-only Terraform MCP Runtime.
- Added ADR 0010 for the single SharePoint upload tool, fail-fast input
  behavior, AWS-defined triple-underscore tool name, and
  delegated/application lane names.
- Updated the architecture flow and added a Claude Code documentation-to-Git/TFE
  sequence in Mermaid and editable Draw.io form.
- Updated the architecture, delegated sequence, application sequence, editable
  Draw.io sources, and rendered diagrams for the two credential lanes.
- Documented one-codebase/two-environment Terraform model.
- Documented the flat `infra/` Terraform root with resource-focused files
  instead of nested Terraform directories.
- Added ADR 0002 for policy-as-code and DevOps workflow ownership.
- Added ADR 0003 for self-managed Azure DevOps Server hosted on AWS and the
  cloud-owned platform repo.
- Added ADR 0004 for the Claude Code Entra JWT and AWS IAM credential boundary.
- Added DevOps workflow diagrams for MCP server CI/CD, policy CI/CD, Claude
  Code discovery authorization, fixed production agent authorization, Entra
  identity Terraform, AWS AgentCore Terraform, and repo ownership.
- Added an Entra identity configuration workflow diagram.

## Remaining Validation

- Real AgentCore Gateway-to-Runtime target behavior.
- Real AgentCore Gateway initialization, synchronization, and invocation of the
  AWS Knowledge and Microsoft Learn remote MCP endpoints.
- Deployment and negative validation of the Terraform MCP Runtime with only the
  public Registry toolset, no TFE credential, and Terraform operations disabled.
- Vendor schema-drift, rate-limit, data-egress, logging, and target kill-switch
  evidence.
- Claude Code token/header support.
- PrivateLink/private DNS behavior for MCP clients.
- Real Microsoft Graph implementation.
- Final Entra app registration and group/app-role names.
- Approved Entra token flow for Claude Code and Lambda client credentials.
- `nonprod.tfvars` and `prod.tfvars` values for the shared Terraform roots.
- Central ECR base-image scanning, signing, SBOM, and compatibility validation.
- Gateway semantic search behavior with real Claude Code.
- Live AgentCore Cedar `FAIL_ON_ANY_FINDINGS` validation against the deployed
  Gateway schema.
- Live Graph OBO and app-only token exchange with target-tenant credentials.
- Real Graph operations and `Sites.Selected` enforcement for
  application calls.
- Real Azure DevOps variable groups, environments, approvals, image scanning,
  SBOM, and signing configuration.
- Central TFE admin repo workspace setup for `identity/entra` and `infra`.
