# ADR 0005: Path-Scoped Policy PR Validation

Date: 2026-07-10

Status: Accepted for PoC validation

## Context

The Enterprise MCP policy source controls which callers can discover and invoke
MCP tools. Invalid policy changes must not merge just because the central TFE
admin repo also runs Terraform plan automation for the pull request.

The repo is hosted in on-prem Azure DevOps Server. For Azure Repos PRs, merge
blocking validation is configured as a branch policy build validation on the
protected branch. The policy CI YAML can define push path filters, but the PR
merge gate must be configured in Azure DevOps branch policies.

## Decision

Configure `policy-ci.yml` as a required Azure DevOps build validation policy on
the protected branch, normally `main`.

Use an automatic required build policy with a path filter matching the policy
bundle and the files that can affect policy validation:

```text
/examples/enterprise_mcp_platform/policy/*;
/examples/enterprise_mcp_platform/policy/generated/*;
/examples/enterprise_mcp_platform/requirements.txt;
/examples/enterprise_mcp_platform/pipelines/azure-devops/policy-ci.yml
```

If the example becomes its own repo root, remove the
`/examples/enterprise_mcp_platform` prefix.

The policy CI gate validates:

- `policy/tool_allowlist.yaml` against `policy/tool_allowlist.schema.json`
- subject, tool, and resource references
- embedded positive and negative policy tests
- generated runtime JSON freshness
- generated JSON and schema JSON parsing

The central TFE admin repo remains responsible for Terraform plan/apply
automation. TFE plan results do not replace policy CI for policy bundle changes.

## Consequences

Positive:

- Policy-only PRs do not need to run unrelated server image validation.
- Invalid policy YAML, stale generated JSON, and broken policy tests block
  merge before deployment.
- Terraform PR automation can keep running independently without becoming the
  policy schema gate.
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
- Decide whether generated Gateway Cedar policy artifacts should be covered by
  the same policy path filter once implemented.
