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
  tool_allowlist.yaml          human-maintained authorization matrix
  tool_allowlist.schema.json   JSON Schema for the YAML format
  generated/
    tool_allowlist.json        generated runtime policy artifact
servers/
  sharepoint_mcp/              implemented example
  crm_mcp/                     placeholder boundary
  internal_software_mcp/       placeholder boundary
clients/                       validation clients
  entra_token_helper.ps1        Windows PowerShell delegated/app-only token helper
identity/
  entra/                       cloud-owned Entra Terraform root
gateway/                       optional Gateway-adjacent code
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
  agentcore_runtime.tf         one AgentCore Runtime per enabled MCP server
  agentcore_gateway.tf         shared AgentCore Gateway and runtime targets
  gateway_private_access.tf    private interface endpoint for Gateway access
  envs/
    nonprod.tfvars             nonprod values
    prod.tfvars                prod values
```

## Server Boundary Rule

Each server owns one downstream system boundary:

- `sharepoint_mcp` owns Microsoft Graph / SharePoint tools.
- `crm_mcp` will own CRM / Dataverse tools.
- `internal_software_mcp` will own internal software API tools.

Do not place CRM tools in the SharePoint MCP server just because the Gateway is
central. The central point is the Gateway, not one huge codebase with every
business-system tool in one file.

## Local SharePoint Test

```bash
cd examples/enterprise_mcp_platform
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export GRAPH_DRY_RUN=true
export MCP_SUBJECT=local-dev-user
export MCP_CLIENT_ID=claude-code-mcp-client-id
export MCP_GROUPS=mcp-sharepoint-readers
export MCP_APP_ROLES=MCP.SharePoint.Read
export MCP_SCOPES=mcp.invoke
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

The Python file under `gateway/` is only an optional Lambda interceptor example
for sanitized caller-context headers.

This setup uses Entra ID with Gateway `CUSTOM_JWT`. It does not deploy Cognito
or AgentCore Identity. AgentCore Identity should only be evaluated later if a
real outbound-token brokering requirement appears.

Claude Code uses an Entra delegated access token as the MCP caller credential.
The MCP request to the AWS-side Gateway uses `Authorization: Bearer <Entra JWT>`.
AWS IAM roles are used after the request reaches AWS infrastructure, such as the
Gateway role invoking Runtime and the Runtime role accessing AWS services.

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
  gateway_private_access.tf
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

Both environment runs deploy all enabled `mcp_servers` entries from the
selected tfvars file.

SharePoint is enabled in the example. CRM and internal software are shown as
disabled entries until their tool contracts are approved.

## Entra Token Examples

Example Entra Terraform for the Enterprise MCP API, Claude Code client, People
Assist client, app roles, and optional Conditional Access lives in:

```text
identity/entra/
```

Claude Code/developer delegated token:

```powershell
Set-Location examples/enterprise_mcp_platform
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:ENTRA_CLIENT_ID = "<interactive-mcp-public-client-id>"
$env:ENTRA_MCP_AUDIENCE = "api://enterprise-mcp-nonprod"
$env:ENTRA_ACCESS_TOKEN = & .\clients\entra_token_helper.ps1 delegated
```

Pass that token to the Claude Code MCP client or validation client as the bearer
token. Do not SigV4-sign the MCP request from Claude Code; IAM is not the MCP
caller identity.

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
export ENTERPRISE_MCP_URL="https://gateway-id.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"
export ENTRA_ACCESS_TOKEN="<entra-token>"
export AGENTCORE_TOOL_SEARCH_QUERY="find SharePoint file read tools"
python clients/gateway_semantic_search.py
```

This tests Gateway discovery only. The returned tool still needs Gateway policy
approval and Runtime input validation before it can be invoked.

## Policy As Code

Policy owners edit:

```text
policy/tool_allowlist.yaml
```

CI validates it against:

```text
policy/tool_allowlist.schema.json
```

Runtime containers load:

```text
policy/generated/tool_allowlist.json
```

Regenerate and validate the runtime artifact with:

```bash
cd examples/enterprise_mcp_platform
python policy/validate_policy.py
python policy/validate_policy.py --check
```

The YAML includes embedded policy test cases for caller/tool/resource decisions.
For example, SharePoint readers can discover SharePoint read tools but cannot
call CRM write tools, and People Assist cannot use semantic search.

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
/examples/enterprise_mcp_platform/policy/generated/*;
/examples/enterprise_mcp_platform/requirements.txt;
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
111122223333.dkr.ecr.us-west-2.amazonaws.com/internal/mcp-python-base:2026-07-04
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
