# ADR 0005: Path-Scoped Policy PR Validation

Date: 2026-07-10

Status: Accepted for PoC validation

The generated-policy validation details below are superseded by ADR 0006. The
required path-scoped branch-policy gate remains in force for direct Cedar.

## Context

The Enterprise MCP direct Cedar source controls which callers can discover and
invoke MCP tools. Invalid policy changes must not merge just because the central TFE
admin repo also runs Terraform plan automation for the pull request.

The repo is hosted in self-managed Azure DevOps Server on AWS. For Azure Repos
PRs, merge
blocking validation is configured as a branch policy build validation on the
protected branch. The policy CI YAML can define push path filters, but the PR
merge gate must be configured in Azure DevOps branch policies.

## Decision

Configure `policy-ci.yml` as a required Azure DevOps build validation policy on
the protected branch, normally `main`.

Use an automatic required build policy with a path filter matching the direct
Cedar source and the files that can affect policy validation:

```text
/examples/enterprise_mcp_platform/policy/*;
/examples/enterprise_mcp_platform/policy/cedar/*;
/examples/enterprise_mcp_platform/pipelines/azure-devops/policy-ci.yml
```

If the example becomes its own repo root, remove the
`/examples/enterprise_mcp_platform` prefix.

The policy CI gate validates that:

- direct Cedar files exist and are non-empty;
- every file targets the AgentCore Gateway resource type;
- legacy YAML, schema, and generated policy artifacts have not returned; and
- the reviewed Cedar source is the artifact promoted to deployment.

AgentCore policy create/update with `FAIL_ON_ANY_FINDINGS` performs the
authoritative validation against the live Gateway-generated schema.

The central TFE admin repo remains responsible for Terraform plan/apply
automation. TFE plan results do not replace policy CI for direct Cedar changes.

## Consequences

Positive:

- Policy-only PRs do not need to run unrelated server image validation.
- Missing or structurally invalid direct Cedar source blocks merge before
  deployment.
- Terraform PR automation can keep running independently without becoming the
  live Gateway-schema validation gate.
- The same repo can keep policy, infra, identity, and server code while still
  applying path-scoped controls.

Tradeoffs:

- Azure DevOps branch policies must be configured outside this repo.
- Path filters must be updated if the folder is promoted to a standalone repo
  or if policy validation dependencies move.
- A PR that changes both policy and Terraform may have both policy CI and TFE
  checks to satisfy.

## Follow-Up Work

- Configure the required build validation policy in the real Azure DevOps
  project.
- Add required reviewers for `policy/` changes.
- Wire direct Cedar into Terraform policy resources and retain AgentCore
  validation findings as deployment evidence.
