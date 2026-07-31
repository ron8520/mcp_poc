# Azure DevOps Workflows

These diagrams describe the cloud-team-owned operating model for the
self-managed Azure DevOps Server repository hosted on AWS. The repo keeps
identity, AWS infrastructure, policy, shared runtime helpers, and MCP server
code together, while still keeping clear folder boundaries and separate
Terraform state per root/environment.

## MCP Server CI/CD

```mermaid
flowchart TD
    Dev["Cloud team changes MCP server code"] --> PR["Azure DevOps pull request"]
    PR --> Paths["Path filter\nservers/**, common/**, requirements"]
    Paths --> Agent["Self-hosted Azure DevOps agent"]
    Agent --> Install["Create Python venv and install dependencies"]
    Install --> Compile["Compile common + selected server Python"]
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
    Owner["Cloud team edits direct Cedar"] --> PR["Azure DevOps pull request"]
    PR --> BranchPolicy["Required Azure DevOps build validation\npath filter: policy folder"]
    PR --> TFE["Central TFE PR automation may also run\nfor Terraform root changes"]
    BranchPolicy --> Source["Check Cedar files are present and non-empty"]
    Source --> Shape["Reject legacy YAML/schema/generated artifacts"]
    Shape --> Gate["Failed policy CI blocks merge"]
    Gate --> Review["Cloud/security/downstream owner review"]
    Review --> Merge["Merge to main"]
    Merge --> Artifact["Optional reviewed Cedar source artifact"]
    Artifact --> TFEAdmin["Central TFE admin repo manages Terraform pipeline"]
    TFEAdmin --> Validate["AgentCore validates direct Cedar\nFAIL_ON_ANY_FINDINGS"]
    Validate --> Nonprod["Nonprod LOG_ONLY + negative tests"]
    Nonprod --> Enforce["Promote to ENFORCE after evidence"]
```

For Azure Repos, the merge-blocking check is the branch policy build
validation, not the YAML `pr` trigger. Configure `policy-ci.yml` as a required
build validation policy on `main` with a path filter matching:

```text
/examples/enterprise_mcp_platform/policy/*;
/examples/enterprise_mcp_platform/policy/cedar/*;
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
    Claude["Employee uses Claude Code to update<br>infra Terraform or tfvars"] --> PR["Azure DevOps pull request"]
    PR --> Review["Cloud/security/network review"]
    Review --> TFEAdmin["Central TFE admin repo-created workspace\nruns plan/apply automatically"]
    TFEAdmin --> Gateway["AgentCore Gateway\nCUSTOM_JWT"]
    TFEAdmin --> Runtime["AgentCore Runtime per enabled credential lane\nplus Registry-only Terraform MCP"]
    TFEAdmin --> VendorTargets["Direct AWS Knowledge and Microsoft Learn targets"]
    TFEAdmin --> Interceptor["Gateway REQUEST interceptor"]
    TFEAdmin --> Policy["Direct Cedar policies"]
    Network["Network/platform account"] --> PrivateLink["Existing Gateway interface endpoint/private DNS"]
    Gateway --> Policy
    Gateway --> Interceptor
    Gateway --> VendorTargets
    Gateway --> Targets["Runtime-hosted targets use IAM/SigV4"]
    Targets --> Runtime
    Runtime --> Downstream["MCP servers use lane-specific downstream credentials"]
```

The documentation targets can inform Claude Code, but they are not part of the
Git or deployment path. Claude Code writes the local checkout, Azure DevOps
Server owns Git/PR controls, and central TFE owns plan/apply. See
`claude-code-terraform-docs-sequence.mmd`.

## Claude Code Tool Discovery And Authorization

```mermaid
sequenceDiagram
    participant Employee as "Employee"
    participant Script as "Token helper script"
    participant Claude as "Claude Code"
    participant Entra as "Microsoft Entra ID"
    participant GW as "AgentCore Gateway"
    participant Cedar as "Direct Cedar policy"
    participant Interceptor as "OBO assertion interceptor"
    participant RT as "SharePoint delegated Runtime"
    participant Graph as "Microsoft Graph"
    participant SP as "SharePoint"

    Employee->>Script: Run entra_token_helper.ps1 delegated
    Script->>Entra: Start device-code flow for api://enterprise-mcp-<env>/mcp.invoke
    Entra-->>Script: Device-code sign-in instructions
    Script-->>Employee: Display sign-in instructions
    Employee->>Entra: Complete authentication
    Script->>Entra: Poll token endpoint
    Entra-->>Script: JWT with user, client, scope, roles/groups
    Script-->>Employee: Return token to ENTRA_ACCESS_TOKEN assignment
    Employee->>Claude: Start MCP client with the environment token
    Claude->>GW: HTTPS MCP call with Authorization: Bearer Entra JWT
    GW->>GW: Validate JWT issuer, audience, client
    GW->>Cedar: Authorize discoverable sharepoint-delegated actions
    Cedar-->>GW: Authorized tool subset for this caller
    GW-->>Claude: Relevant and authorized tool candidates
    Claude->>GW: Call selected MCP tool with same Entra bearer token
    GW->>Cedar: Authorize exact action and context.input
    Cedar-->>GW: Allow or deny
    GW->>Interceptor: If allowed, pass validated bearer for delegated action
    Interceptor-->>GW: x-mcp-user-assertion
    GW->>RT: SigV4 invoke sharepoint-delegated target with assertion
    RT->>RT: Reject invalid site_id, file_path, or content
    RT->>Entra: OBO exchange for Graph
    Entra-->>RT: Delegated Graph token
    RT->>Graph: Upload file as employee
    Graph->>SP: Enforce native employee ACL
    SP-->>Graph: Result or access denied
    Graph-->>RT: Result
    RT-->>GW: MCP tool result
    GW-->>Claude: MCP response
```

## Application Credential Authorization

```mermaid
sequenceDiagram
    participant PA as "Scheduler / background AI job"
    participant Entra as "Microsoft Entra ID"
    participant GW as "AgentCore Gateway"
    participant Cedar as "Direct Cedar policy"
    participant RT as "SharePoint application Runtime"
    participant SP as "SharePoint / Graph"

    PA->>Entra: Client credentials token for api://enterprise-mcp-<env>/.default
    Entra-->>PA: App-only JWT with app role
    PA->>GW: Call predefined SharePoint MCP tool
    GW->>GW: Validate JWT issuer, audience, client
    GW->>Cedar: Authorize exact sharepoint-application upload action
    Cedar-->>GW: Allow or deny
    GW->>RT: If allowed, SigV4 invoke without user assertion
    RT->>RT: Reject invalid site_id, file_path, or content
    RT->>Entra: Client credentials for Microsoft Graph
    Entra-->>RT: Graph application token
    RT->>SP: Upload file as application
    SP->>SP: Enforce Graph permissions and Sites.Selected
    SP-->>RT: Result
    RT-->>GW: MCP result
    GW-->>PA: Response
```

## Cloud-Owned Repo Boundaries

```mermaid
flowchart LR
    subgraph Repo["enterprise-mcp-platform on Azure DevOps Server"]
        Policy["policy/cedar/\ndirect AgentCore Cedar"]
        Servers["servers/\nSharePoint, CRM, internal software MCP"]
        Identity["identity/entra/\nEntra apps, app roles, Conditional Access"]
        Infra["infra/\nAgentCore Gateway, Runtime, IAM, direct Cedar"]
        Pipelines["pipelines/azure-devops/\npolicy and image CI/CD"]
        TFEAdmin["central TFE admin repo\nworkspace/pipeline automation"]
        Network["network/platform repo\nPrivateLink, DNS, routing"]
    end

    Policy -->|"Gateway policy source"| Infra
    Identity -->|"audience, discovery URL, client IDs"| Infra
    Servers -->|"final image URIs"| Infra
    Network -->|"existing network prerequisites"| Infra
    Pipelines --> Policy
    Pipelines --> Servers
    TFEAdmin --> Identity
    TFEAdmin --> Infra
```

DevOps ownership should be explicit:

| Area | Primary owner | Required reviewer |
| --- | --- | --- |
| `policy/cedar/*.cedar` | cloud platform team | security/downstream owner for expanded access |
| MCP server source | cloud platform team | downstream system owner for domain behavior |
| MCP Dockerfiles | cloud platform team | DevOps/security for publish controls |
| `pipelines/azure-devops/*.yml` | cloud platform team | DevOps/security |
| `infra/*.tf` | cloud platform team | security/networking as applicable |
| `identity/entra/*.tf` | cloud platform team | identity/security governance |
| `envs/prod.tfvars` | cloud platform team | production change approver |
