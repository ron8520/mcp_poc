# MCP Agent Platform on AWS

This repository contains the SharePoint MCP proof of concept, its AgentCore
Gateway/Runtime configuration, Terraform retained for the long-term platform,
architecture decisions, and operator guidance.

## Start here

The current PoC workflow is documented in [docs/clickops.md](docs/clickops.md):

**EC2 workspace → CodeCommit → manual ARM64 image build/push to ECR → AgentCore
Runtime and Gateway configuration in the AWS Console.**

CodeCommit and ECR pushes do not automatically deploy a Runtime or update a
Gateway. This is a deployment procedure, not evidence that AWS, Entra ID,
Microsoft Graph, or SharePoint has been configured or validated. No Terraform
apply is part of this PoC stage.

## Current implementation and target

- SharePoint is the only active service boundary. CRM and internal software
  directories are placeholders, not deployed servers.
- The service pins MCP Python SDK 2.2.0 and serves Streamable HTTP on
  0.0.0.0:8000/mcp. An ARM64 image build and live Runtime/Gateway invocation
  still require validation.
- The current downstream baseline uses Runtime MSAL for delegated OBO. The
  app-only ingress remains gated. Native AgentCore Identity OBO and per-app M2M
  remain the long-term target; see [ADR 0012](docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md)
  and [ADR 0013](docs/adr/0013-staged-entra-app-only-catalog-and-bau-rollout.md).
- Terraform is retained as the long-term infrastructure path: one TFE
  workspace/state per environment composed from infra/deployment/. It is not
  the current PoC deployment mechanism.
- MCP protocol dates and SDK package versions are distinct. The AWS Gateway
  configuration lists 2026-07-28, 2025-11-25, 2025-06-18, and
  2025-03-26; the managed Gateway dialect must be checked against the selected
  date before compatibility is claimed.

## Repository map

| Path | Responsibility |
| --- | --- |
| docs/clickops.md | Current EC2, CodeCommit, ECR, Runtime, Gateway, and Entra operator path. |
| servers/sharepoint_mcp/ | SharePoint MCP server and Microsoft Graph behavior. |
| gateway/ | Gateway interceptor and its tests. |
| policy/ | Direct Cedar authorization source. |
| clients/ | Local and Gateway validation clients. |
| infra/deployment/ | Long-term one-environment Terraform composition root. |
| infra/modules/entra/ | Long-term Entra registration module. |
| infra/modules/agentcore/ | Long-term AWS AgentCore module. |
| pipelines/azure-devops/ | Optional future CI/CD reference; not configured for this PoC. |
| images/mcp_python_base/ | Optional future base image; service builds do not depend on it. |
| docs/adr/ | Preserved architecture decision history. |
| END_GOAL.md | Long-term outcome and success criteria. |
| WHAT_WE_HAVE_DONE.md | Decisions and repository work completed so far. |
| IN_PROGRESS.md | Validation gates and unfinished work. |

## Architecture references

- [Current and target SharePoint identity routing](docs/architecture/sharepoint-identity-routing.md)
- [Detailed developer architecture guide](docs/architecture/enterprise-mcp-platform-internal-review.md)
- [Canonical editable layered diagram](docs/architecture/enterprise-mcp-platform-layered.drawio)
- [Current PoC diagram preview](docs/architecture/enterprise-mcp-platform-current-poc.svg)
- [Target identity diagram preview](docs/architecture/enterprise-mcp-platform-target-identity.svg)
- [Archived diagrams and generators](docs/architecture/history/README.md)
- [Current-stage ADR 0014](docs/adr/0014-single-repo-clickops-poc-and-protocol-compatibility.md)

The current PoC diagram describes repository components and the intended
manual workflow; it is not proof of a live deployment. The target diagram
describes accepted identity decisions that still require non-production
validation.
