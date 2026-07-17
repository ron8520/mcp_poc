# Cloud-Owned Repository Boundaries

This PoC assumes the cloud team owns the MCP server code, Entra identity
Terraform, AWS AgentCore infrastructure, policy YAML, and Azure DevOps
pipelines for nonprod and prod.

Because one team owns the full control plane, a separate policy repo is not
required now. Keep one repo with clear folder boundaries:

| Folder | Purpose | Owner |
| --- | --- | --- |
| `policy/` | MCP authorization YAML, JSON Schema, generated runtime JSON | cloud platform team |
| `identity/entra/` | Entra app registrations, app roles, optional Conditional Access | cloud platform team |
| `infra/` | AWS AgentCore Gateway, Runtime, IAM, and PrivateLink Terraform | cloud platform team |
| `servers/sharepoint_mcp/` | SharePoint MCP server | cloud platform team with SharePoint owner review |
| `servers/crm_mcp/` | CRM MCP server boundary | cloud platform team with CRM owner review |
| `servers/internal_software_mcp/` | internal API MCP server boundary | cloud platform team with internal API owner review |
| `common/mcp_runtime/` | shared runtime helpers | cloud platform team |
| `pipelines/azure-devops/` | policy and MCP image CI/CD pipelines | cloud platform team with DevOps/security review |

Use Azure DevOps branch policies and path-based reviewers instead of splitting
repositories too early.

Configure `policy-ci.yml` as a required Azure DevOps build validation policy
with a path filter for `policy/`, `policy/generated/`, the policy pipeline YAML,
and shared policy validation dependencies. This keeps invalid policy bundles
from merging even if central TFE plan automation also runs for the PR.

Recommended reviewer rules:

```text
policy/**                         cloud platform + security/downstream owner
identity/entra/**                 cloud platform + identity/security
infra/**                          cloud platform + security/network
servers/sharepoint_mcp/**         cloud platform + SharePoint owner
servers/crm_mcp/**                cloud platform + CRM owner
pipelines/azure-devops/**         cloud platform + DevOps/security
```

Keep these contracts stable:

- Policy owners maintain `tool_allowlist.yaml`.
- Policy CI validates YAML against `tool_allowlist.schema.json`.
- Policy CI checks `generated/tool_allowlist.json` is current.
- Policy CI is a required, path-scoped Azure DevOps branch-policy gate before
  merge.
- Identity Terraform produces Entra audience, discovery URL, and client IDs for
  the AWS Gateway configuration.
- MCP server CI builds final service images only from approved source and
  generated policy.
- Infrastructure consumes final image URIs through `envs/nonprod.tfvars` and
  `envs/prod.tfvars`.
- Terraform plan/apply automation is created by the central TFE admin repo.
- Production image publish requires Azure DevOps approvals.

Consider separate repos only if ownership or release cadence changes, such as a
separate security team owning policy independently from the cloud team.
