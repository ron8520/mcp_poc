# ADR 0003: Azure DevOps Cloud-Owned Platform Repo

Date: 2026-07-06

Status: Accepted for PoC validation

The YAML/generated-policy workflow below is superseded by ADR 0006. The
single-repo and Azure DevOps ownership decisions remain in force. ADR 0013
supersedes the separate-TFE-state execution detail below: `identity/entra` and
`infra` remain module boundaries, while the composed `deployment/` root owns one
workspace/state per environment.

## Context

The platform repository is hosted in self-managed Azure DevOps Server on AWS.
The cloud team owns
the MCP server code, Cedar policy, Entra identity Terraform, and AWS AgentCore
infrastructure Terraform for nonprod and prod.

Terraform repository/workspace creation and Terraform execution pipelines are
managed automatically by the central TFE admin repo, not by Azure DevOps YAML in
this repository.

ADR 0002 introduced policy-as-code and workflow examples using GitHub Actions
and a possible future multi-repo split. That no longer matches the operating
model.

## Decision

Use one cloud-owned platform repo with clear folder boundaries:

```text
examples/enterprise_mcp_platform/
  deployment/
  identity/entra/
  infra/
  policy/
  servers/
  common/
  pipelines/azure-devops/
```

Use Azure DevOps Server YAML pipelines under:

```text
examples/enterprise_mcp_platform/pipelines/azure-devops/
```

Pipeline responsibilities:

- `policy-ci.yml`: validate the direct Cedar source layout and publish reviewed
  policy source when requested.
- `mcp-server-ci.yml`: compile MCP server code, build service images, and
  optionally push to central ECR.

Do not define Terraform plan/apply pipelines here. The central TFE admin repo
creates one workspace/state and execution pipeline per environment for the
composed `deployment/` root. The composed root calls the two module boundaries:

```text
deployment/main.tf
  module.entra    -> ../identity/entra
  module.platform -> ../infra
```

Use `deployment/envs/nonprod.tfvars` and `deployment/envs/prod.tfvars` for the
environment runs. The direct module directories remain available for narrow
local validation and are not separate production TFE states.

Use Azure DevOps branch policies, path-based reviewers, secure variable groups,
self-hosted agents, and approval gates for image publish. Use the central TFE
admin process for Terraform plan/apply approvals.

ADR 0005 defines the required, path-scoped Azure DevOps build validation policy
for direct Cedar pull requests.

## Consequences

Positive:

- One cloud team can maintain the full MCP control plane in one repo.
- Policy, identity, infrastructure, and server code stay visibly connected.
- Azure DevOps Server matches the actual source-control and non-Terraform
  pipeline platform.
- Module boundaries remain visible while one environment state keeps Entra and
  AgentCore wiring atomic; nonprod and prod still have separate state and
  approval paths.
- Terraform automation stays consistent with the enterprise central TFE admin
  model.
- A separate policy repo is not required until ownership or release cadence
  changes.

Tradeoffs:

- Pipeline examples assume self-hosted agents have Python, Docker, and AWS CLI
  available.
- Azure DevOps secure variables and image publish approvals must be configured
  outside this repo.
- Terraform workspace setup and apply behavior are delegated to the central TFE
  admin repo.
- The repo must rely on branch policies/path reviewers to prevent broad access
  changes from being merged without the right approvals.

## Follow-Up Work

- Configure Azure DevOps variable groups for central ECR publish credentials.
- Configure Azure DevOps approvals for image publish.
- Confirm the central TFE admin repo points at the composed `deployment/` root
  with the correct nonprod/prod tfvars and reviewed state migration plan, if an
  existing standalone state is being moved.
- Add the real central ECR registry and production agent pool names.
- Add image scanning, SBOM, and signing steps once the internal tooling is
  confirmed.
