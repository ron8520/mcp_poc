# Infrastructure

This directory is the AgentCore platform Terraform module. The central TFE
execution path is the composed `../deployment` root, which calls this module as
`module.platform` and calls `../identity/entra` as `module.entra` in the same
environment state.

For narrow local validation of this module, initialize without a backend and
run the module tests:

```bash
terraform init -backend=false
terraform validate
terraform test
```

Use `../deployment/README.md` for the central TFE run path, environment plan
selection and state-migration warning. Do not create a separate production TFE
state for this module.

Resource files in this Terraform root are split by ownership:

- `iam.tf`: AgentCore trust roles, Cedar evaluation permissions, and
  lane-scoped secret access.
- `agentcore_runtime.tf`: current PoC AgentCore Runtime per enabled service
  identity lane.
- `agentcore_gateway.tf`: shared AgentCore Gateway, direct Cedar policies, and
  targets.
- `gateway_interceptor.tf`: request interceptor Lambda that propagates the
  validated user assertion only to OBO lanes.

Recommended split:

- Deployment environment tfvars: `environment`, `target_account_id`, `region`,
  existing Runtime subnet IDs/security groups, image tags, and enabled MCP
  servers.
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
while policy mode is `LOG_ONLY` and while the target caller-context gate remains
unvalidated. Terraform rejects `true` unless `gateway_policy_mode = "ENFORCE"`;
enabling it removes the transitional global `mcp.invoke` requirement so app-only
tokens can reach Cedar. This is a current PoC gate, not proof that the target
app-only identity composition is implemented.

## Target AgentCore Identity and trust-domain sizing (staged path; live validation required)

The current Terraform shape is two fixed SharePoint lanes using one immutable
image, with app-only ingress gated off. The accepted target creates one
application Runtime per approved trust domain, not per caller or provider and
not a universal all-provider Runtime. A thin default-deny resolver may select
multiple approved provider profiles inside that domain; a new Runtime is
normally required only for a new audit/IAM/credential-isolation boundary.

Both target OAuth lane types use AgentCore Identity. Delegated Runtime/workload
IAM may access only approved OBO provider ARNs, while application Runtime/
workload IAM may access only approved M2M provider ARNs. Wildcard, cross-lane,
cross-server, and cross-domain provider access must be denied and tested.

The staged resolver key is validated caller client ID + exact target-qualified
action + server-owned resource key + environment. Callers cannot provide auth
mode/provider alias/ARN/client ID/secret or `resource_ref`; SharePoint keeps the
existing `site_id` unchanged as its resource key. Mapping/config/provider misses
fail closed without provider disclosure. The deployment root delivers the
schema-1 `APP_ONLY_MAPPING_JSON` value, capped at 5000 characters; a statically
pinned AgentCore Configuration Bundle is optional and deferred. Cache, rollback,
kill switch, drift detection, audit, quota and non-production negative tests
remain gates. Provider registration, caller application credential provisioning
and their credential methods remain unresolved. See
[`../../../docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md`](../../../docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md).

The TFE execution identity that creates or updates Cedar must have
`bedrock-agentcore:InvokeGateway` on the managed Gateway in addition to policy
management permissions. That external administrative role is intentionally not
the Gateway execution role managed by this root.
