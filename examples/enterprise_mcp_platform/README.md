# Enterprise MCP Platform Example

This is a reference structure for an enterprise MCP platform repo.

It is not one SharePoint-only folder. The Gateway is shared, and every
downstream system gets its own MCP server boundary.

## Layout

```text
images/
  mcp_python_base/             platform-owned base container image
common/
  mcp_runtime/                 shared runtime helpers only
policy/
  README.md                    policy boundary and deployment workflow
  cedar/
    sharepoint-delegated.cedar delegated-access tool authorization
    sharepoint-application.cedar app-only tool authorization
servers/
  sharepoint_mcp/              implemented example
  crm_mcp/                     placeholder boundary
  internal_software_mcp/       placeholder boundary
clients/                       validation clients
  entra_token_helper.ps1        Windows PowerShell delegated/app-only token helper
identity/
  entra/                       cloud-owned Entra Terraform root
gateway/
  obo_assertion_interceptor.py trusted delegated-token propagation
pipelines/
  azure-devops/
    mcp-server-ci.yml          MCP server build/test/publish example
    policy-ci.yml              policy validation/publish example
repo_boundaries/               cloud-owned repo boundary guidance
infra/
  main.tf                      shared Terraform root
  providers.tf                 provider requirements
  variables.tf                 root inputs
  outputs.tf                   root outputs
  iam.tf                       IAM roles and policies
  agentcore_runtime.tf         one AgentCore Runtime per enabled credential lane
  agentcore_gateway.tf         shared AgentCore Gateway and runtime targets
  gateway_interceptor.tf       OBO assertion interceptor Lambda
  envs/
    nonprod.tfvars             nonprod values
    prod.tfvars                prod values
```

The Terraform root currently deploys AgentCore Gateway/Runtime only in Sydney
(`ap-southeast-2`). Melbourne (`ap-southeast-4`) remains gated until AWS
publishes the required service endpoints and VPC support and a non-production
deployment is validated. The target account ID and Runtime network IDs are
supplied by central platform/TFE configuration. Gateway PrivateLink and private
DNS are managed in the external network/platform account and are intentionally
not created by this root.

## Server Boundary Rule

Each server owns one downstream system boundary:

- `sharepoint_mcp` owns Microsoft Graph / SharePoint tools.
- `crm_mcp` will own CRM / Dataverse tools.
- `internal_software_mcp` will own internal software API tools.

Do not place CRM tools in the SharePoint MCP server just because the Gateway is
central. The central point is the Gateway, not one huge codebase with every
business-system tool in one file.

## Local SharePoint Test

The server images use Python MCP SDK 2.0 and `MCPServer`. The local client pins
the `2026-07-28` protocol for direct server validation. AgentCore Gateway
clients remain on SDK 2 with `mode="legacy"` until AWS supports and validates
the `2026-07-28` protocol; this does not require a separate server image.

```bash
cd examples/enterprise_mcp_platform
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export GRAPH_DRY_RUN=true
python -m servers.sharepoint_mcp.src.server
```

In another terminal:

```bash
cd examples/enterprise_mcp_platform
. .venv/bin/activate
python clients/local_client.py
```

## Gateway Deployment

AgentCore Gateway is not a Lambda handler. It is deployed through Terraform in
`infra/agentcore_gateway.tf`.

The request interceptor under `gateway/` is part of the SharePoint OBO lane. It
copies the Gateway-validated bearer token into `x-mcp-user-assertion` only for
`sharepoint-delegated___*` calls. The delegated target and Runtime are the only
resources that allowlist that header. The application lane never receives it.

This setup uses Entra ID with Gateway `CUSTOM_JWT`. It does not deploy Cognito
or AgentCore Identity. AgentCore Identity should only be evaluated later if a
real outbound-token brokering requirement appears.

The employee runs `entra_token_helper.ps1 delegated` to obtain an Entra
delegated access token and assign it to `ENTRA_ACCESS_TOKEN`. Claude Code does
not authenticate the employee or request the token; it only reads the
environment variable and sends `Authorization: Bearer <Entra JWT>` to the
AWS-side Gateway. AWS IAM roles are used after the request reaches AWS
infrastructure, such as the Gateway role invoking Runtime and the Runtime role
accessing AWS services.

Terraform is under:

```text
infra/
  main.tf
  providers.tf
  variables.tf
  outputs.tf
  iam.tf
  agentcore_runtime.tf
  agentcore_gateway.tf
  gateway_interceptor.tf
  envs/
    nonprod.tfvars
    prod.tfvars
```

For central TFE Terraform runs, use `infra` as the working directory for both
nonprod and prod. Configure the workspace/run to select the appropriate var
file:

```text
nonprod -> terraform plan -var-file=envs/nonprod.tfvars
prod    -> terraform plan -var-file=envs/prod.tfvars
```

If applies are configured separately, use the same var-file values with
`terraform apply`.

Each enabled `mcp_servers` entry owns one service image. Terraform flattens its
enabled `lanes` into Runtime/target pairs. The SharePoint entry therefore
deploys `sharepoint-delegated` and `sharepoint-application` from the exact same
image URI without duplicating the service build.

SharePoint is enabled in the example. CRM is a disabled one-lane
`crm-application` example until its tool contracts and downstream identity
model are approved. Add a CRM delegated lane only if the CRM API must preserve
delegated end-user identity; two lanes are not a universal requirement.

## Entra Token Examples

Example Entra Terraform for the Enterprise MCP API, Claude Code client, People
Assist client, app roles, and optional Conditional Access lives in:

```text
identity/entra/
```

Employee delegated token for Claude Code:

```powershell
Set-Location examples/enterprise_mcp_platform
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:ENTRA_CLIENT_ID = "<interactive-mcp-public-client-id>"
$env:ENTRA_MCP_AUDIENCE = "api://enterprise-mcp-nonprod"
$env:ENTRA_ACCESS_TOKEN = & .\clients\entra_token_helper.ps1 delegated
```

The employee runs this command; the helper performs the device-code flow and
the PowerShell assignment stores its returned token in `ENTRA_ACCESS_TOKEN`.
Claude Code only reads and sends that token. Do not SigV4-sign the MCP request
from Claude Code; IAM is not the MCP caller identity.

Generic AI application or other service app-only token:

```powershell
Set-Location examples/enterprise_mcp_platform
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:ENTRA_CLIENT_ID = "<application-client-id>"
$env:ENTRA_CLIENT_SECRET = "<from approved secret store>"
$env:ENTRA_ACCESS_TOKEN = & .\clients\entra_token_helper.ps1 client-credentials
```

This PowerShell helper is for Windows validation. Deployed LangGraph,
LangChain, or LlamaIndex applications should acquire their app-only token in
application code or through the approved workload-identity integration.

## Semantic Search Smoke Test

Gateway semantic search is enabled in Terraform. Test the built-in search tool
with:

```bash
cd examples/enterprise_mcp_platform
export ENTERPRISE_MCP_URL="https://gateway-id.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp"
export ENTRA_ACCESS_TOKEN="<entra-token>"
export AGENTCORE_TOOL_SEARCH_QUERY="find the SharePoint file upload tool"
python clients/gateway_semantic_search.py
```

This tests Gateway discovery only. The returned tool still needs Gateway policy
approval and Runtime input validation before it can be invoked.

## Policy As Code

Policy owners edit Cedar directly:

```text
policy/cedar/sharepoint-delegated.cedar
policy/cedar/sharepoint-application.cedar
```

There is no YAML abstraction, generated JSON, or Runtime policy copy. AgentCore
Gateway is the single tool-authorization point. During Terraform
create/update, `aws_bedrockagentcore_policy` uses
`validation_mode = "FAIL_ON_ANY_FINDINGS"` so AgentCore validates each
statement against the live Gateway schema.

The delegated Cedar policy grants separate read and upload capabilities;
Microsoft Graph OBO and native SharePoint permissions decide which sites and
items the employee may access. The application Cedar policy grants the same
capability split to a service principal; Graph application permissions and
`Sites.Selected` decide its site boundary. The upload tool accepts only
`site_id`, `file_path`, and `content`, and raises an error without changing
invalid values.

AgentCore Gateway exposes these tools as
`sharepoint-delegated___sharepoint_upload_file` and
`sharepoint-application___sharepoint_upload_file`. The three underscores are
AWS's fixed `<TargetName>___<ToolName>` separator, not a convention introduced
by this repository.

## Azure DevOps CI/CD

Azure DevOps Server pipeline examples live in:

```text
pipelines/azure-devops/
  mcp-server-ci.yml
  policy-ci.yml
```

They use `examples/enterprise_mcp_platform/...` paths because this example is
nested in the current repo. If the folder is promoted to its own Azure DevOps
repo later, remove that path prefix from pipeline triggers and scripts.

Terraform plan/apply pipeline YAML is intentionally not defined here. The
central TFE admin repo creates the Terraform workspaces and execution pipeline
for `identity/entra` and `infra`.

For Azure Repos PR validation, configure `policy-ci.yml` as a required branch
policy build validation on the protected branch. The branch policy, not the
YAML `pr` trigger, is what blocks PR completion. Use this path filter while the
example remains nested in this repo:

```text
/examples/enterprise_mcp_platform/policy/*;
/examples/enterprise_mcp_platform/policy/cedar/*;
/examples/enterprise_mcp_platform/pipelines/azure-devops/policy-ci.yml
```

If this example becomes a standalone repo, remove the
`/examples/enterprise_mcp_platform` prefix from each path.

Detailed workflow diagrams and ownership guidance:

- [DevOps workflows](/Users/ronruan/Desktop/mcp_poc/docs/architecture/devops-workflows.md)
- [Cloud-owned repo boundaries](/Users/ronruan/Desktop/mcp_poc/examples/enterprise_mcp_platform/repo_boundaries/README.md)

## Optional Base Image Pattern

Current MCP server Dockerfiles are self-contained and do not require a shared
base image.

The optional future platform image would use a URI like:

```text
111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/internal/mcp-python-base:2026-07-04
```

The optional base-image example lives in:

```text
images/mcp_python_base/
```

Future optional build order:

1. Platform pipeline builds, scans, signs, and publishes `mcp-python-base`.
2. Service pipeline builds `sharepoint-mcp`, `crm-mcp`, or another server image
   from that base only if the platform adopts the pattern.
3. Terraform deploys AgentCore Runtime using the final service image URI.

The base image is for shared container mechanics only. Do not put SharePoint,
CRM, internal API code, downstream credentials, or caller-specific access policy
in it.
