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

This is intentionally separate from `infra/`, which owns AWS AgentCore
resources. The same cloud team can own both roots, but the state and apply
scope should stay separate.

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

Use this folder as a separate identity workspace/root:

```text
examples/enterprise_mcp_platform/identity/entra
```

Pipeline var-file selection:

```text
nonprod -> terraform plan -var-file=envs/nonprod.tfvars
prod    -> terraform plan -var-file=envs/prod.tfvars
```

If applies are configured separately:

```text
nonprod -> terraform apply -var-file=envs/nonprod.tfvars
prod    -> terraform apply -var-file=envs/prod.tfvars
```

Outputs consumed by AWS `infra/`:

- `enterprise_mcp_discovery_url`
- `enterprise_mcp_audience`
- `claude_code_client_id`
- `people_assist_client_id`

Keep `create_people_assist_client_secret = false` unless cloud/security
governance has approved storing that secret in Terraform state. Prefer the
enterprise secret management process for production client credentials.

Terraform execution is handled by the central TFE admin repo, which creates the
repo/workspaces and plan/apply automation for this root.
