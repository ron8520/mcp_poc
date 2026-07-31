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

- `iam.tf`: AgentCore trust roles, Cedar evaluation permissions, and
  lane-scoped secret access.
- `agentcore_runtime.tf`: one AgentCore Runtime per enabled service identity
  lane.
- `agentcore_gateway.tf`: shared AgentCore Gateway, direct Cedar policies, and
  targets.
- `gateway_interceptor.tf`: request interceptor Lambda that propagates the
  validated user assertion only to OBO lanes.

Recommended split:

- Environment tfvars: `environment`, `target_account_id`, `region`, existing
  Runtime subnet IDs/security groups, image tags, and enabled MCP servers.
- TFE workspace variables, variable sets, or approved dynamic credentials: AWS
  provider authentication and other backend credentials.
- Lane configuration contains Secrets Manager ARNs, never secret values.
  Runtime roles receive `GetSecretValue` only for their lane. If a secret uses
  a customer-managed KMS key, also configure the lane's
  `secret_kms_key_arns`.

Do not use `terraform.workspace` to decide production behavior inside the code.
Make the environment explicit in `nonprod.tfvars` and `prod.tfvars` so plans are
easy to review.

The workload root currently deploys AgentCore Gateway/Runtime only in Sydney
(`ap-southeast-2`). Melbourne (`ap-southeast-4`) remains gated until AWS
publishes the required service endpoints and VPC support and a non-production
deployment is validated. The root does not use `aws_caller_identity` or
`aws_region` data sources: the central platform/TFE configuration supplies
`target_account_id`, and all regional ARNs use `var.region`.

AgentCore Gateway PrivateLink is an external prerequisite. The network/platform
account owns the interface endpoint, private DNS, endpoint policy, routing, and
client-side security groups. This root intentionally does not contain
`gateway_private_access.tf`; it creates the workload resources and consumes
existing Runtime subnet/security-group IDs.

`gateway_app_only_ingress_enabled` is a guarded cutover switch. Keep it `false`
while policy mode is `LOG_ONLY`. Terraform rejects `true` unless
`gateway_policy_mode = "ENFORCE"`; enabling it removes the transitional global
`mcp.invoke` requirement so app-only tokens can reach Cedar.

The TFE execution identity that creates or updates Cedar must have
`bedrock-agentcore:InvokeGateway` on the managed Gateway in addition to policy
management permissions. That external administrative role is intentionally not
the Gateway execution role managed by this root.
