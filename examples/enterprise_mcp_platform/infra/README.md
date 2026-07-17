# Infrastructure

This directory is the Terraform root for the enterprise MCP platform.

Use this directory as the Terraform root for both central TFE environment
workspaces/runs:

```text
nonprod -> examples/enterprise_mcp_platform/infra
prod    -> examples/enterprise_mcp_platform/infra
```

The code is identical for both environments. Environment differences come from
the var file selected by the central TFE workspace/run configuration:

```text
nonprod -> terraform plan -var-file=envs/nonprod.tfvars
prod    -> terraform plan -var-file=envs/prod.tfvars
```

If applies are configured separately:

```text
nonprod -> terraform apply -var-file=envs/nonprod.tfvars
prod    -> terraform apply -var-file=envs/prod.tfvars
```

For local validation, use the same var files explicitly:

```bash
terraform plan -var-file=envs/nonprod.tfvars
terraform plan -var-file=envs/prod.tfvars
```

Resource files in this Terraform root are split by ownership:

- `iam.tf`: AgentCore trust roles and inline policies.
- `agentcore_runtime.tf`: one AgentCore Runtime per enabled MCP server.
- `agentcore_gateway.tf`: shared AgentCore Gateway, policy engine, and targets.
- `gateway_private_access.tf`: interface endpoint and private access policy.

Recommended split:

- Environment tfvars: `environment`, subnet IDs, security groups,
  Gateway endpoint VPC, image tags, enabled MCP servers.
- TFE workspace variables, variable sets, or approved dynamic credentials: AWS
  provider authentication and other backend credentials.
- Sensitive workspace variables: Entra client secrets for Lambda runtime only
  if injected through the application deployment path. Do not put secrets in
  Terraform state unless the owning security team approves that pattern.

Do not use `terraform.workspace` to decide production behavior inside the code.
Make the environment explicit in `nonprod.tfvars` and `prod.tfvars` so plans are
easy to review.
