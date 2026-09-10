# Cloud-Owned Repository Boundaries

This platform assumes the cloud team owns the MCP server code, Entra identity
Terraform, AWS AgentCore infrastructure, direct Cedar policy, and Azure DevOps
pipelines for nonprod and prod.

Because one team owns the full control plane, a separate policy repo is not
required now. Keep one repo with clear folder boundaries:

| Folder | Purpose | Owner |
| --- | --- | --- |
| `policy/` | Direct AgentCore Cedar authorization source | cloud platform team |
| `deployment/` | Composed environment Terraform root; one TFE workspace/state per environment | cloud platform team |
| `identity/entra/` | Entra Terraform module for app registrations, app roles, optional Conditional Access | cloud platform team |
| `infra/` | AWS AgentCore Gateway, Runtime, IAM, and Cedar Terraform module; consumes existing platform network inputs | cloud platform team |
| `servers/sharepoint_mcp/` | SharePoint MCP server | cloud platform team with SharePoint owner review |
| `servers/crm_mcp/` | CRM MCP server boundary | cloud platform team with CRM owner review |
| `servers/internal_software_mcp/` | internal API MCP server boundary | cloud platform team with internal API owner review |
| `common/mcp_runtime/` | shared runtime helpers | cloud platform team |
| `pipelines/azure-devops/` | policy and MCP image CI/CD pipelines | cloud platform team with DevOps/security review |

Use Azure DevOps branch policies and path-based reviewers instead of splitting
repositories too early.

Configure `policy-ci.yml` as a required Azure DevOps build validation policy
with a path filter for `policy/cedar/` and the policy pipeline YAML. This keeps
invalid policy changes from merging even if central TFE plan automation also
runs for the PR.

Recommended reviewer rules:

```text
policy/**                         cloud platform + security/downstream owner
identity/entra/**                 cloud platform + identity/security
deployment/**                     cloud platform + identity/security/network
infra/**                          cloud platform + security/network
servers/sharepoint_mcp/**         cloud platform + SharePoint owner
servers/crm_mcp/**                cloud platform + CRM owner
pipelines/azure-devops/**         cloud platform + DevOps/security
```

Keep these contracts stable:

- Policy owners maintain only reviewed `.cedar` files.
- AgentCore create/update with `FAIL_ON_ANY_FINDINGS` validates Cedar against
  the live Gateway schema.
- Policy CI is a required, path-scoped Azure DevOps branch-policy gate before
  merge.
- The composed deployment Terraform wires Entra audience, discovery URL, and
  client IDs into the AWS Gateway configuration in the same environment state.
- The app-only catalog creates registrations, service principals and role/
  permission assignments but not caller passwords, certificates or federated
  credentials; approved credential provisioning remains a separate gate.
- MCP server CI builds final service images only from approved server source.
- The deployment root consumes final image URIs through its
  `envs/nonprod.tfvars` and `envs/prod.tfvars`.
- Terraform plan/apply automation is created by the central TFE admin repo.
- Production image publish requires Azure DevOps approvals.

Consider separate repos only if ownership or release cadence changes, such as a
separate security team owning policy independently from the cloud team.
