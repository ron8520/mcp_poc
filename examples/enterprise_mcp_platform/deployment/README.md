# Composed Environment Deployment

This directory is the central Terraform working directory for one environment.
The composed root keeps the Entra and AWS module boundaries while one Terraform
Enterprise (TFE) workspace and state owns the environment's Enterprise MCP API,
per-workload caller and downstream applications, AgentCore Gateway, Runtime,
and their wiring.

The module references are explicit:

```text
module.entra    -> ../identity/entra
module.platform -> ../infra
```

Use separate TFE workspaces and state for `nonprod` and `prod`. Select the
environment with the reviewed var-file; do not use a shared state across
environments.

## Run path

From the repository root, the offline/local validation path is:

```bash
cd examples/enterprise_mcp_platform/deployment
terraform init -backend=false
terraform validate
terraform test
```

`terraform test` uses the checked-in provider mocks. A local plan with the
placeholder environment values is only a structural check; a meaningful plan
requires real TFE-provided variables, provider authentication and target
account/network values. For a plan, use the same directory and var-file that
central TFE will use:

```bash
terraform plan -var-file=envs/nonprod.tfvars
```

Central TFE owns the backend, workspace variables, execution identity,
approvals, plan and apply. An approved apply uses the same working directory and
var-file selection:

```bash
terraform apply -var-file=envs/nonprod.tfvars
```

Use `envs/prod.tfvars` for production plan/apply selection. The corresponding
offline module checks are:

```bash
(cd ../infra && terraform init -backend=false && terraform validate && terraform test)
(cd ../identity/entra && terraform init -backend=false && terraform validate)
```

The repository's Python checks use the same commands as the service pipeline:

```bash
cd ..
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s servers/sharepoint_mcp -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s gateway -p 'test_*.py'
```

The local Terraform checks and Python tests are not live Entra, AgentCore,
Gateway, Graph, SharePoint, PrivateLink or TFE evidence.

The checked-in environment files contain placeholders and are not deployment
credentials. Replace them only through the approved TFE/secret-management
process. Sydney (`ap-southeast-2`) is the only currently accepted AgentCore
region; the target account, Runtime subnets and security groups are supplied by
central platform/TFE configuration. Gateway PrivateLink, private DNS, endpoint
policy and routing remain owned by the external network/platform account.

## Identity and app-only inputs

The root passes the Entra module outputs into the platform module, including the
Enterprise MCP API audience and the allowed caller client IDs. The default
`app_only_apps = {}` keeps per-workload app creation disabled in the environment
examples. An enabled catalog entry has this shape:

```hcl
app_only_apps = {
  stable_workload_name = {
    owner = "<entra-owner-object-guid>"
    grants = {
      "<sharepoint-site-id>" = [
        "sharepoint_list_site_content",
        "sharepoint_get_file_text",
      ]
    }
  }
}
```

Each entry creates a separate Entra caller application/service principal and
downstream SharePoint application/service principal. App-only roles are assigned
directly to the caller service principal; delegated user groups remain on the
delegated path. The catalog grants exact `site_id` to tool combinations and
does not replace Gateway Cedar or SharePoint authorization.

`app_only_provider_bindings` is an explicit handoff from a logical workload to
an already-registered AgentCore OAuth provider ARN. This root does not register
that provider or select its credential method. When the binding map is non-empty,
the platform module builds the immutable schema-1 `APP_ONLY_MAPPING_JSON`
Runtime value, capped at 5000 characters and containing no provider secret. The
staged Runtime branch remains behind
`gateway_app_only_ingress_enabled = false` until provider registration, caller
context, Cedar `ENFORCE`, live M2M, and downstream grant evidence are accepted.

For example, the binding shape names an existing provider and contains no
credential value:

```hcl
app_only_provider_bindings = {
  stable_workload_name = "arn:aws:bedrock-agentcore:ap-southeast-2:<account-id>:token-vault/default/oauth2-credential-provider/<provider-name>"
}
```

The provider ARN must be supplied through the approved AgentCore handoff. The
caller application's authentication method (password, certificate or
federated credential) and the downstream provider credential method are both
separate unresolved implementation gates; this input does not make either
application able to obtain a token.

Terraform represents Graph `Sites.Selected` admin consent for each downstream
application. The explicit per-site permission grant is not created here; the
`app_only_site_grants` output is a desired grant description for the separate
downstream-owner/admin handoff.

The inactive example at
`examples/app-only-two-apps.tfvars` shows the catalog shape only. It leaves
provider bindings empty and must not be treated as live identity or Graph
evidence.

## State migration warning

The composed root is the execution path. Moving an existing environment from a
standalone `identity/entra` or `infra` state changes Terraform addresses by
adding module prefixes. Do not invent addresses or run bulk `terraform state
mv`/`import` commands from this example. Before migration, back up the exact
TFE state and produce a reviewed plan against that state; use only the
address-specific `moved` or import procedure approved by the platform/TFE owner.
Do not apply until the plan proves that existing resources are retained rather
than recreated.

The standalone module directories remain useful as module sources and for
narrow local validation. They are not separate production TFE states under this
deployment model.

## Outputs

The root exposes the composed Entra and AgentCore values needed by operators:

- `enterprise_mcp_application_client_id`
- `enterprise_mcp_audience`
- `enterprise_mcp_discovery_url`
- `gateway_id`
- `gateway_url`
- `runtime_arns`
- `app_only_identities`
- `app_only_mcp_role_ids`
- `app_only_site_grants` (desired-output handoff, not a created Graph grant)

Successful local validation or a Terraform plan does not prove live Entra,
AgentCore Identity, Gateway, Microsoft Graph, SharePoint, PrivateLink or TFE
behaviour. Record those checks separately in the environment deployment
evidence.
