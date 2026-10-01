# MCP Agent Platform on AWS

This repository contains the SharePoint MCP proof of concept, its AgentCore
Gateway/Runtime configuration, Terraform retained for the long-term platform,
architecture decisions, and operator guidance.

## Start here

The current PoC workflow is documented in [docs/clickops.md](docs/clickops.md):

**EC2 workspace → CodeCommit → manual ARM64 image build/push to ECR → AgentCore
Runtime and Gateway configuration in the AWS Console.**

CodeCommit and ECR pushes do not automatically deploy a Runtime or update a
Gateway. This is a deployment procedure, not evidence that AWS, Entra ID,
Microsoft Graph, or SharePoint has been configured or validated. No Terraform
apply is part of this PoC stage.

## Current implementation and target

- Phase one includes SharePoint and a separate CRM MCP server, both implemented
  locally. CRM exposes one app-only operation to update a Dynamics 365
  case summary using a separate Entra app through AgentCore Identity M2M; see
  [CRM setup and contract](servers/crm_mcp/README.md) and
  [ADR 0015](docs/adr/0015-dynamics-case-summary-app-only.md).
  Actual column configuration and live identity/permissions/deployment validation
  remain pending. Internal software remains outside phase one.
- The SharePoint service pins MCP Python SDK 2.2.0 and serves Streamable HTTP on
  0.0.0.0:8000/mcp. The rewritten servers pass local source, startup and HTTP
  checks. ARM64 image builds and live Runtime/Gateway invocation still require
  validation for this implementation.
- Every SharePoint Runtime must set `GRAPH_AUTH_MODE` explicitly to `obo`,
  `client_credentials`, or `agentcore_m2m`. Tool calls use Microsoft Graph;
  local tests replace Graph and token providers with mocks and are not live
  deployment evidence.
- The current downstream baseline uses Runtime MSAL for delegated OBO. The
  app-only ingress remains gated. Native AgentCore Identity OBO and per-app M2M
  remain the long-term target; see [ADR 0012](docs/adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md)
  and [ADR 0013](docs/adr/0013-staged-entra-app-only-catalog-and-bau-rollout.md).
- Terraform is retained as the long-term infrastructure path: one TFE
  workspace/state per environment composed from infra/deployment/. It is not
  the current PoC deployment mechanism.
- MCP protocol dates and SDK package versions are distinct. The AWS Gateway
  configuration lists 2026-07-28, 2025-11-25, 2025-06-18, and
  2025-03-26; the managed Gateway dialect must be checked against the selected
  date before compatibility is claimed.

## Repository map

| Path | Responsibility |
| --- | --- |
| docs/clickops.md | Current EC2, CodeCommit, ECR, Runtime, Gateway, and Entra operator path. |
| servers/sharepoint_mcp/ | SharePoint MCP server and Microsoft Graph behavior. |
| servers/crm_mcp/ | Dynamics 365 case-summary MCP server and its separate application identity. |
| gateway/ | Gateway interceptor and its tests. |
| policy/ | Direct Cedar authorization source. |
| infra/deployment/ | Long-term one-environment Terraform composition root. |
| infra/modules/entra/ | Long-term Entra registration module. |
| infra/modules/agentcore/ | Long-term AWS AgentCore module. |
| pipelines/azure-devops/ | Optional future CI/CD reference; not configured for this PoC. |
| docs/architecture/ | Current reviews and two diagram families; older references are under archive/. |
| docs/adr/ | Seven core decisions in the reading index, with all decision history preserved. |
| WHAT_WE_HAVE_DONE.md | Decisions and repository work completed so far. |

## Python source and tests

Each server keeps implementation in `src/` and tests in a separate sibling
`tests/` directory. `server.py` registers tools and shows the request steps;
`auth.py` handles downstream identity. SharePoint's `app_auth.py` handles its
per-caller AgentCore M2M mapping, while `graph.py` contains Graph calls and PDF
extraction. CRM's `dataverse.py` contains its single-field PATCH. There is no
generic service layer or shared cross-server credential helper.

Gateway interceptor tests live in `gateway/tests/`. Tests are local-only and
ignored by Git, including the Terraform mock tests. A fresh clone will not
contain them; keep a separate backup if they need to be preserved or shared.

| Test file | What it protects |
| --- | --- |
| `sharepoint_mcp/tests/test_graph.py` | Graph operations, pagination, site binding and PDF limits. |
| `sharepoint_mcp/tests/test_auth.py` | OBO and fixed client-credentials token acquisition. |
| `sharepoint_mcp/tests/test_app_auth.py` | Per-app identity routing and authorization isolation. |
| `sharepoint_mcp/tests/test_server.py` | Strict inputs before credentials, tool results and Streamable HTTP headers. |
| `crm_mcp/tests/test_auth.py` | Signed application callers, explicit case grants and CRM M2M identity. |
| `crm_mcp/tests/test_dataverse.py` | Summary-only PATCH without upsert, redirects or retries. |
| `crm_mcp/tests/test_server.py` | CRM tool contract and request ordering. |
| `gateway/tests/test_obo_assertion_interceptor.py` | Gateway assertion forwarding for the correct lane. |

For a local checkout that has these test files, run from the repository root
after installing the project dependencies:

```bash
python -m pip install -r requirements.txt -r servers/sharepoint_mcp/requirements.txt -r servers/crm_mcp/requirements.txt pytest
python -m pytest --import-mode=importlib servers/sharepoint_mcp/tests servers/crm_mcp/tests gateway/tests
```

Terraform tests remain locally in their component-specific `tests/` directories.
CI no longer runs the local-only tests; it retains compilation, SDK import,
image build, and policy-source checks. `.dockerignore` excludes tests from the
image build context.

## Architecture references

The current architecture has three reading entry points:

| Document | Audience and purpose |
| --- | --- |
| [Phase-one internal review](docs/architecture/enterprise-mcp-platform-internal-review.md) | Shareable overview of SharePoint, CRM, data flow, ownership and security boundaries. References use official AWS/Microsoft documentation. |
| [SharePoint identity routing](docs/architecture/sharepoint-identity-routing.md) | Engineering reference for current and target identity flows. |
| [Engineering findings and release gates](docs/architecture/sharepoint-first-slice-review.md) | Open findings, responsible teams and required acceptance evidence. |

Maintain these two diagram families:

| Family | Editable source and previews |
| --- | --- |
| Phase-one review | [Draw.io workflows](docs/architecture/sharepoint-review-workflows.drawio), embedded PNGs in the internal review, and three Mermaid sequence sources. |
| Current/target platform | [Layered Draw.io](docs/architecture/enterprise-mcp-platform-layered.drawio), [current PoC SVG](docs/architecture/enterprise-mcp-platform-current-poc.svg), and [target identity SVG](docs/architecture/enterprise-mcp-platform-target-identity.svg). |

The [ADR reading index](docs/adr/README.md) separates seven core decisions from
historical and future references. All 15 ADR files retain their original numbers
and paths. [Archived architecture references](docs/architecture/archive/README.md)
contain the earlier diagram family and optional future workflows. Older
ADR-linked Mermaid/Draw.io sources remain available for historical traceability.

The current PoC diagram describes repository components and the intended
manual workflow; it is not proof of a live deployment. The target diagram
describes accepted identity decisions that still require non-production
validation.
