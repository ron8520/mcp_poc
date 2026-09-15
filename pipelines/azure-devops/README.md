# Azure DevOps Pipelines

These pipeline examples are written for an on-prem Azure DevOps Server repo
owned by the cloud team.

The examples assume self-hosted Linux agents with:

- Python 3.11 or newer
- Docker with ARM64 build support for the SharePoint AgentCore Runtime image
- AWS CLI, for central ECR publish
- network access to central ECR

Do not store secrets in YAML. Use Azure DevOps secure variables, variable
groups, service connections, managed identity on the agent, or your approved
enterprise credential injection pattern.

Terraform plan/apply pipelines are intentionally not defined here. The central
TFE admin repo creates the Terraform repositories/workspaces and controls the
Terraform execution pipeline automatically.

## Pipelines

| Pipeline | Purpose |
| --- | --- |
| `policy-ci.yml` | Check the direct Cedar source layout and optionally publish the reviewed source bundle. |
| `mcp-server-ci.yml` | Compile MCP server Python, run SharePoint unit tests, build Docker images, and optionally push to central ECR. |

## Recommended Azure DevOps Setup

Create separate Azure DevOps pipelines pointing at these YAML files:

```text
pipelines/azure-devops/policy-ci.yml
pipelines/azure-devops/mcp-server-ci.yml
```

For Azure Repos, pull request validation is enforced by branch policies. Do
not rely on the YAML `pr` block for the merge gate. Configure `policy-ci.yml`
as a required build validation policy on the protected branch.

Recommended `policy-ci.yml` branch policy:

```text
Branch: main
Build pipeline: policy-ci.yml
Trigger: Automatic
Policy requirement: Required
Path filter:
  /examples/enterprise_mcp_platform/policy/*;
  /examples/enterprise_mcp_platform/policy/cedar/*;
  /examples/enterprise_mcp_platform/pipelines/azure-devops/policy-ci.yml
```

If this example folder becomes the repo root, remove the
`/examples/enterprise_mcp_platform` prefix from the path filter.

The policy validation gate is independent of TFE. The central TFE admin repo
may still run plan automation for Terraform roots, but a policy PR should not
be mergeable unless the required `policy-ci.yml` branch policy passes.

Use the same branch-policy pattern for `mcp-server-ci.yml` if server/image
changes should also be required before merge. Keep it as a separate build
validation policy with server, common helper, requirements, and server
pipeline YAML path filters so policy-only PRs and server-code PRs can be gated
independently.

Protect production changes with:

- branch policies on `main`
- required reviewers for `policy/`, `identity/entra/`, `infra/`, and
  `pipelines/`
- manual approval gates for image publish stages
- restricted variable groups for central ECR publish credentials

## Pipeline Variables

Common variables:

```text
AZDO_AGENT_POOL              self-hosted cloud agent pool name
PYTHON_EXECUTABLE            python3
AWS_REGION                   ap-southeast-2
INTERNAL_ECR_REGISTRY        111122223333.dkr.ecr.ap-southeast-2.amazonaws.com/internal
```

AWS publish variables should come from a restricted variable group or the
self-hosted agent identity:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN            optional
```
