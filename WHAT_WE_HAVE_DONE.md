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
- Clarified that lane selection follows the downstream security subject rather
  than the client product: an employee-facing AI app uses delegated/OBO when
  user ACLs must apply, while a truly autonomous workflow uses M2M.
- Selected AgentCore Identity as the target outbound OAuth broker for both
  delegated/OBO and autonomous M2M lanes, with separate workload identities and
  provider-ARN IAM boundaries. The current direct MSAL/client-credentials PoC
  remains unchanged until validation passes.
- Added ADR 0013 for the staged Entra app-only catalog and BAU rollout. The
  catalog is keyed by stable workload name and records an owner plus
  `site_id -> exact MCP tools`; each enabled entry creates a separate caller
  Entra app/service principal and downstream SharePoint app/service principal.
  App-only grants are direct; sensitivity groups are not used, while delegated
  user groups remain separate. The registration path does not create a caller
  password, certificate or federated credential.
- Added a composed `deployment/` Terraform root that wires
  `module.entra -> ../identity/entra` and `module.platform -> ../infra` in one
  TFE workspace/state per environment. The app-only catalog is opt-in with an
  empty default, and the platform module receives the resulting caller IDs and
  explicit provider-binding handoff.
- Added the staged app-only Runtime adapter: explicit
  `GRAPH_AUTH_MODE=agentcore_m2m`, signed application-token revalidation,
  exact caller/action/site/tool checks, trusted caller context, and per-request
  AgentCore M2M token calls. Its local tests pass, but this does not prove live
  AgentCore, Entra, provider, or Graph behavior.
- Kept provider registration and its credential method unresolved. The
  `app_only_provider_bindings` map is an explicit logical-app to already-
  registered provider-ARN handoff, not native provider provisioning. Graph
  `Sites.Selected` admin consent is represented by Terraform; the explicit
  per-site grant remains a separate downstream-owner/admin handoff. Caller
  application credential provisioning is also unresolved; Entra/AD sync alone
  does not make an app-only caller able to obtain a token.
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
- Clarified the current identity boundary: Entra remains the caller-token
  issuer, while Gateway `CUSTOM_JWT` validation is the managed AgentCore
  Identity inbound authorization capability. The current repository PoC has no
  outbound credential provider or token vault; ADR 0012 records the separate
  target OBO/M2M validation decision.
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
- dry-run Graph client plus live default-library listing, pagination, and
  bounded PDF text extraction
- Exact SharePoint item/drive/site response binding plus 25 MiB and 250-page PDF
  limits before extraction; short-lived Graph download URLs are fetched without
  the Graph bearer token
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
- Composed deployment root for one environment TFE state, including Entra
  caller/downstream identity outputs and platform wiring
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
- Composed deployment root for nonprod and prod environment runs, with one TFE
  workspace/state per environment
- Windows PowerShell Entra token helper for delegated and app-only token examples
- Terraform Gateway Entra `allowed_clients` input
- Entra identity Terraform example for Enterprise MCP API, Claude Code client,
  People Assist client, app roles, and optional Conditional Access
- Runtime IAM trust conditions and observability permissions
- Runtime request metadata allowlist
- Azure DevOps MCP server CI/CD pipeline example
- SharePoint unit-test execution and ARM64 image build in the MCP server
  pipeline for AgentCore Runtime
- Azure DevOps policy CI/CD pipeline example
- Azure DevOps policy CI branch-policy path filter guidance
- cloud-owned repo boundary documentation

## Documentation

- Updated README with the shared Gateway and separate MCP server architecture.
- Added architecture and sequence diagrams to README.
- Added an editable draw.io version of the Claude Code identity sequence and embedded its rendered PNG in the developer architecture guide.
- Retired the generated Word report as an architecture source; the Markdown
  architecture documents are authoritative for navigation, implementation
  status, verification guidance, and known gaps.
- Updated ADR 0001 with the AgentCore Gateway for MCP decision.
- Added Claude Code and People Assist sequence diagrams to ADR.
- Documented the AWS-managed Gateway URL and no-CloudFront decision.
- Documented the optional base-image build sequence.
- Documented AWS sample learnings, the current inbound/no-outbound-provider
  boundary, the historical target in ADR 0011, and the superseding OBO/M2M
  target decision in ADR 0012.
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
- Added ADR 0011 for the accepted-for-PoC-validation identity-routing target:
  delegated two-hop audience-specific OBO, trust-domain app-only Runtime
  sizing, and a default-deny provider resolver. ADR 0011 explicitly preserves
  the current fixed-lane PoC as the implementation baseline.
- Added ADR 0012, superseding ADR 0011 for the target identity decision. It uses
  AgentCore Identity for both delegated/OBO and autonomous M2M, keeps the lanes
  and provider IAM isolated, generalizes future-server resource routing, and
  preserves the current fixed-lane PoC as the implementation baseline.
- Added ADR 0013 for the staged app-only catalog, bounded mapping delivery,
  provider-binding gate, shared Runtime IAM union, and BAU/revocation sequence.
- Added the Markdown identity-routing source at
  `docs/architecture/sharepoint-identity-routing.md`, with separate current
  PoC and target validation flows and the resolver contract.
- Added the editable layered architecture source and 1920 x 1080 current/target
  previews. The reference-led layout now presents Shared Services/ECR above the
  platform, identity and callers on the left, Gateway and Cedar centrally,
  Runtime-hosted MCP servers and tool contracts by lane, and downstream systems
  on the right. It retains separate Network/Platform and MCP Workload accounts,
  marks gated and future paths explicitly, and uses orthogonal straight segments.
- Updated the architecture flow and added a Claude Code documentation-to-Git/TFE
  sequence in Mermaid and editable Draw.io form.
- Updated the architecture, delegated sequence, application sequence, editable
  Draw.io sources, and rendered diagrams for the two credential lanes.
- Updated the target architecture to distinguish employee-facing AI apps from
  autonomous workflows and to show both identity lanes using lane-scoped
  AgentCore Identity providers.
- Documented one-codebase/two-environment Terraform model with one composed TFE
  workspace/state per environment.
- Updated the layered and identity-routing architecture sources for the stable
  app-only catalog, bounded `APP_ONLY_MAPPING_JSON` delivery, explicit provider
  binding, and shared Runtime IAM union. Regenerated their editable and SVG
  exports; PNG render checks remain part of validation.
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
- Synchronized the README, end goal, and progress documents so target identity
  behavior is not described as current implementation.
- Recorded the MCP release boundary: `2025-11-25` is current stable and
  `2026-07-28` is an RC/target requiring managed Gateway dialect validation.

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
- Replace the current delegated Lambda assertion-copy/MSAL path only after
  non-production proves Gateway-audience -> Runtime-audience -> Graph-audience
  OBO; OBO remains delegated-user-only.
- Replace the current direct Runtime client-credentials path only after
  non-production proves AgentCore Identity M2M, lane-scoped provider IAM, and
  application-grant denial for unapproved downstream resources.
- Validate the preferred app-only `x-mcp-caller-assertion` PoC gate, including
  Runtime-only Gateway SigV4 ingress and revalidation of `iss`, Gateway `aud`,
  `exp`, `tid`, `azp`/`appid`, and `roles`; app-only ingress remains gated off.
- Validate one application Runtime per approved trust domain and the thin
  resolver platform key (caller client ID, target-qualified action,
  server-owned downstream resource key, environment). Preserve SharePoint's
  existing `site_id`, keep provider selection out of caller input, and fail
  closed.
- Validate trust-domain IAM provider-ARN boundaries and the shared Runtime's
  union-of-provider blast radius. Validate the bounded 5000-character
  `APP_ONLY_MAPPING_JSON` delivery and explicit `app_only_provider_bindings`;
  a pinned private S3 snapshot may be evaluated later, while Configuration
  Bundle delivery is optional and deferred.
- Validate onboarding/BAU gates: caller app role, Cedar rule, resolver mapping,
  reviewed config version, non-production negative tests, and production
  promotion; create a Graph provider only for a distinct downstream identity,
  permission or audit boundary, and a Runtime only for a new trust domain.
- Real Graph operations and `Sites.Selected` enforcement for
  application calls.
- Real Azure DevOps variable groups, environments, approvals, image scanning,
  SBOM, and signing configuration.
- Central TFE admin repo workspace setup for the composed `deployment/` root,
  with `identity/entra` and `infra` retained as module boundaries.
