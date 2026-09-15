# Entra Identity Terraform

This folder is the cloud-team-owned Terraform root for the MCP Entra auth
model.

It creates:

- `enterprise-mcp-api-{environment}` as the protected API / token audience.
- `mcp.invoke` delegated scope for Claude Code and other delegated clients.
- app roles for SharePoint read, SharePoint publish, CRM admin, and People
  Assist SharePoint read.
- `claude-code-mcp-client-{environment}` as a public client/token-helper app.
- `people-assist-mcp-client-{environment}` as a confidential service app.
- optional report-only Conditional Access policy for trusted internal network
  access.

This remains a separate Terraform module boundary from `infra/`, which owns AWS
AgentCore resources. The central execution path composes both modules from
`../deployment` so one TFE workspace and state owns the complete environment;
the module boundary does not imply a separate production state.

## Public Access Note

Entra app registrations do not have a storage-account-style "disable public
network access" setting. Restrict access with:

- single-tenant app registrations
- app assignment required
- admin consent
- app roles
- Conditional Access
- trusted named locations based on approved corporate egress CIDRs
- compliant-device or MFA controls where required

If ExpressRoute/Microsoft peering routes the traffic privately, that improves
network path control, but Entra token issuance should still be governed by
Conditional Access and assignment.

## Terraform Usage

Use the composed environment root for central TFE runs:

```text
examples/enterprise_mcp_platform/deployment
```

From that directory, select the environment explicitly:

```bash
terraform plan -var-file=envs/nonprod.tfvars
terraform plan -var-file=envs/prod.tfvars
```

An approved apply uses the same composed root and var-file. Do not create a
separate production TFE state for this module. The direct `identity/entra`
directory and its environment examples remain available for narrow module
validation; they are not the central deployment path.

Outputs wired by the composed `deployment/` root into AWS `infra`:

- `enterprise_mcp_discovery_url`
- `enterprise_mcp_audience`
- `claude_code_client_id`
- `people_assist_client_id`

Keep `create_people_assist_client_secret = false` unless cloud/security
governance has approved storing that secret in Terraform state. Prefer the
enterprise secret management process for production client credentials.

The client product does not choose the downstream lane. An employee-facing AI
application uses an approved delegated grant when downstream user permissions
must apply. A scheduler or workflow uses an application role and client
credentials only when no employee is the security subject. Target downstream
OBO and M2M credential-provider registrations are separate from this current
caller-registration example and are brokered through AgentCore Identity under
ADR 0012; do not reuse the Gateway-audience token as a downstream token.

The app-only catalog creates caller and downstream application registrations,
service principals, roles and permission requests; it does not create a caller
password, certificate or federated credential. The caller authentication method
and the downstream AgentCore provider credential method both require a separate
approved implementation. Entra/AD synchronization supplies identity data but
does not by itself provision either credential path, so a catalog entry cannot
acquire an app-only token until those gates are complete.

Terraform execution is handled by the central TFE admin repo, which creates the
environment workspaces and plan/apply automation for the composed
`deployment/` root. See [`deployment/README.md`](../../deployment/README.md) for
the run path and state-migration warning.
