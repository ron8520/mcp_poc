# Azure DevOps Workflows

These diagrams describe the cloud-team-owned operating model for the on-prem
Azure DevOps repository. The repo keeps identity, AWS infrastructure, policy,
shared runtime helpers, and MCP server code together, while still keeping clear
folder boundaries and separate Terraform state per root/environment.

## MCP Server CI/CD

```mermaid
flowchart TD
    Dev["Cloud team changes MCP server code"] --> PR["Azure DevOps pull request"]
    PR --> Paths["Path filter\nservers/**, common/**, generated policy JSON"]
    Paths --> Agent["Self-hosted Azure DevOps agent"]
    Agent --> Install["Create Python venv and install dependencies"]
    Install --> PolicyCheck["Validate generated policy JSON\npython policy/validate_policy.py --check"]
    PolicyCheck --> Compile["Compile common + selected server Python"]
    Compile --> DockerBuild["Build selected server Docker image"]
    DockerBuild --> Review["Branch policy and reviewer approval"]
    Review --> Merge["Merge to main"]
    Merge --> MainBuild["Build image from main"]
    MainBuild --> ManualRun["Manual Azure Pipeline run\npublishImage=true"]
    ManualRun --> Auth["Use restricted AWS variables\nor approved agent identity"]
    Auth --> Push["Push final service image to central ECR"]
    Push --> Tfvars["Update nonprod/prod tfvars image_uri through approved change"]
    Tfvars --> TFEAdmin["Central TFE admin repo manages workspace pipeline"]
    TFEAdmin --> Runtime["AgentCore Runtime pulls final image after apply"]
```

## Policy CI/CD

```mermaid
flowchart TD
    Owner["Cloud team edits tool_allowlist.yaml"] --> PR["Azure DevOps pull request"]
    PR --> BranchPolicy["Required Azure DevOps build validation\npath filter: policy folder"]
    PR --> TFE["Central TFE PR automation may also run\nfor Terraform root changes"]
    BranchPolicy --> Schema["Validate YAML against tool_allowlist.schema.json"]
    Schema --> References["Validate subject, tool, and resource references"]
    References --> Tests["Run embedded policy test cases"]
    Tests --> Generated["Check generated/tool_allowlist.json is up to date"]
    Generated --> Gate["Failed policy CI blocks merge"]
    Gate --> Review["Cloud/security/downstream owner review"]
    Review --> Merge["Merge to main"]
    Merge --> Artifact["Optional Azure DevOps build artifact\nenterprise-mcp-policy"]
    Artifact --> GatewayPolicy["Generate or update Gateway Cedar policy later"]
    Artifact --> RuntimePolicy["Runtime containers consume generated JSON"]
    GatewayPolicy --> TFEAdmin["Central TFE admin repo manages Terraform pipeline"]
    RuntimePolicy --> ServerCI["MCP server CI validates policy compatibility"]
```

For Azure Repos, the merge-blocking check is the branch policy build
validation, not the YAML `pr` trigger. Configure `policy-ci.yml` as a required
build validation policy on `main` with a path filter matching:

```text
/examples/enterprise_mcp_platform/policy/*;
/examples/enterprise_mcp_platform/policy/generated/*;
/examples/enterprise_mcp_platform/requirements.txt;
/examples/enterprise_mcp_platform/pipelines/azure-devops/policy-ci.yml
```

If the example becomes its own repo root, remove the
`/examples/enterprise_mcp_platform` prefix. The central TFE admin repo can keep
running Terraform PR automation independently; policy CI failure must still
block PR completion for matching policy changes.

## Entra Identity Terraform Flow

```mermaid
flowchart TD
    Cloud["Cloud team updates identity/entra Terraform"] --> PR["Azure DevOps pull request"]
    PR --> Review["Cloud/security review"]
    Review --> TFEAdmin["Central TFE admin repo-created workspace\nruns plan/apply automatically"]
    TFEAdmin --> ApiApp["Enterprise MCP API\nscope: mcp.invoke\napp roles"]
    TFEAdmin --> ClaudeClient["Claude Code public client"]
    TFEAdmin --> PeopleClient["People Assist service client"]
    TFEAdmin --> AppRoles["Assign groups/service principals to app roles"]
    TFEAdmin --> CA["Optional report-only Conditional Access\ntrusted internal networks"]
    ApiApp --> Outputs["Audience, discovery URL, client IDs"]
    ClaudeClient --> Outputs
    PeopleClient --> Outputs
    Outputs --> AwsVars["Values copied or exported to AWS infra vars"]
```

## AWS AgentCore Terraform Flow

```mermaid
flowchart TD
    Cloud["Cloud team updates infra Terraform or tfvars"] --> PR["Azure DevOps pull request"]
    PR --> Review["Cloud/security/network review"]
    Review --> TFEAdmin["Central TFE admin repo-created workspace\nruns plan/apply automatically"]
    TFEAdmin --> Gateway["AgentCore Gateway\nCUSTOM_JWT"]
    TFEAdmin --> Runtime["AgentCore Runtime per enabled MCP server"]
    TFEAdmin --> PrivateLink["Gateway interface endpoint/private DNS"]
    Gateway --> Targets["Gateway targets invoke runtimes with IAM role"]
    Runtime --> Downstream["MCP servers call approved downstream systems"]
```

## Claude Code Tool Discovery And Authorization

```mermaid
sequenceDiagram
    participant Dev as "Developer / Claude Code"
    participant Script as "Token helper script"
    participant Entra as "Microsoft Entra ID"
    participant GW as "AgentCore Gateway"
    participant IAM as "AWS IAM roles"
    participant Policy as "Gateway Policy Engine"
    participant RT as "MCP Runtime"
    participant DS as "Downstream system"

    Dev->>Script: Need MCP access token
    Script->>Entra: Request token for api://enterprise-mcp-<env>/mcp.invoke
    Entra-->>Script: JWT with user, client, scope, roles/groups
    Script-->>Dev: Entra bearer token for MCP Gateway
    Dev->>GW: HTTPS MCP call with Authorization: Bearer Entra JWT
    GW->>GW: Validate JWT issuer, audience, client, scope
    GW->>Policy: Partially authorize discoverable MCP tool actions
    Policy-->>GW: Authorized tool subset for this caller
    GW-->>Dev: Relevant and authorized tool candidates
    Dev->>GW: Call selected MCP tool with same Entra bearer token
    GW->>Policy: Authorize exact action and context.input
    Policy-->>GW: Allow or deny
    GW->>IAM: Use Gateway service role after JWT authorization
    GW->>RT: If allowed, invoke Runtime with Gateway IAM role
    RT->>RT: Validate generated policy JSON and tool input constraints
    RT->>DS: Call approved downstream API with downstream credential
    DS-->>RT: Result
    RT-->>GW: MCP tool result
    GW-->>Dev: MCP response
```

## Fixed Production Agent Authorization

```mermaid
sequenceDiagram
    participant PA as "People Assist Lambda"
    participant Entra as "Microsoft Entra ID"
    participant GW as "AgentCore Gateway"
    participant Policy as "Gateway Policy Engine"
    participant RT as "SharePoint MCP Runtime"
    participant SP as "SharePoint / Graph"

    PA->>Entra: Client credentials token for api://enterprise-mcp-<env>/.default
    Entra-->>PA: App-only JWT with app role
    PA->>GW: Call predefined SharePoint MCP tool
    GW->>GW: Validate JWT issuer, audience, client, scope/role
    GW->>Policy: Authorize fixed tool and site constraints
    Policy-->>GW: Allow or deny
    GW->>RT: If allowed, invoke Runtime with Gateway IAM role
    RT->>RT: Validate generated policy JSON and tool input
    RT->>SP: Read approved SharePoint content
    SP-->>RT: Result
    RT-->>GW: MCP result
    GW-->>PA: Response
```

## Cloud-Owned Repo Boundaries

```mermaid
flowchart LR
    subgraph Repo["enterprise-mcp-platform on Azure DevOps Server"]
        Policy["policy/\nYAML, schema, generated JSON"]
        Servers["servers/\nSharePoint, CRM, internal software MCP"]
        Identity["identity/entra/\nEntra apps, app roles, Conditional Access"]
        Infra["infra/\nAgentCore Gateway, Runtime, IAM, PrivateLink"]
        Pipelines["pipelines/azure-devops/\npolicy and image CI/CD"]
        TFEAdmin["central TFE admin repo\nworkspace/pipeline automation"]
    end

    Policy -->|"runtime JSON"| Servers
    Policy -->|"Gateway policy inputs"| Infra
    Identity -->|"audience, discovery URL, client IDs"| Infra
    Servers -->|"final image URIs"| Infra
    Pipelines --> Policy
    Pipelines --> Servers
    TFEAdmin --> Identity
    TFEAdmin --> Infra
```

DevOps ownership should be explicit:

| Area | Primary owner | Required reviewer |
| --- | --- | --- |
| `policy/tool_allowlist.yaml` | cloud platform team | security/downstream owner for expanded access |
| MCP server source | cloud platform team | downstream system owner for domain behavior |
| MCP Dockerfiles | cloud platform team | DevOps/security for publish controls |
| `pipelines/azure-devops/*.yml` | cloud platform team | DevOps/security |
| `infra/*.tf` | cloud platform team | security/networking as applicable |
| `identity/entra/*.tf` | cloud platform team | identity/security governance |
| `envs/prod.tfvars` | cloud platform team | production change approver |
