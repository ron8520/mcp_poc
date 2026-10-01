# Dynamics 365 CRM MCP

Independent app-only MCP server. The only tool is
`crm_update_case_summary(case_id, summary)`: replace a nonempty text summary on
one explicitly authorized Case (`incidentid` GUID, not the display ticket number).
The request cannot choose a field, API URL, provider, or caller identity.

The implementation keeps each boundary visible: `src/server.py` validates the
tool arguments and orders the operation, `src/auth.py` validates the trusted
caller and obtains the dedicated AgentCore M2M token, and `src/dataverse.py`
sends the single Dataverse PATCH.

## Configuration

All values are required. Missing or invalid configuration fails startup.

| Variable | Meaning |
| --- | --- |
| `CRM_BASE_URL` | Dataverse origin, e.g. `https://example.crm6.dynamics.com`, no trailing slash |
| `CRM_SUMMARY_FIELD` | Approved writable text column logical name, e.g. **hypothetical** `new_summary`; verify metadata before deployment |
| `CRM_SUMMARY_MAX_CHARS` | Positive character limit matching that column's metadata |
| `CRM_CALLER_TENANT_ID` | Entra tenant GUID for inbound callers |
| `CRM_CALLER_AUDIENCE` | Gateway API application GUID, never the Dataverse audience |
| `CRM_CALLER_CASES_JSON` | Object mapping each authorized caller client GUID to an explicit nonempty array of case GUIDs; no wildcard |
| `AGENTCORE_WORKLOAD_NAME` | Dedicated CRM workload identity name |
| `CRM_OAUTH_PROVIDER_ARN` | Dedicated AgentCore Identity OAuth2 provider ARN |

Only public-cloud Dataverse `*.crm[region].dynamics.com` origins are supported.
Case and caller GUID grants use exact matching. Keep the PoC grant map within
Runtime environment limits; larger populations require a separate policy design.
Summary is preserved exactly; empty/null values and extra tool arguments are not
part of the contract. Setting the field does not permit setting case ID, user action,
status or any other field. Configuration changes require owner review.

## Identity and deployment

1. Register a **separate downstream Entra application** for CRM per environment.
   Create its Dataverse application user and assign a custom least-privilege
   security role for the approved Case record scope. Apply column security where
   supported. The MCP field restriction does not itself restrict stolen app credentials.
2. Configure a dedicated AgentCore Identity OAuth2 provider with that app's
   credentials and tenant token endpoint. The resource scope is
   `CRM_BASE_URL/.default`. Verify the provider's Entra client-credentials behavior
   live; no direct-secret/MSAL fallback is implemented.
3. Create the CRM workload identity and Runtime role. Restrict
   `GetWorkloadAccessToken` to its workload/directory and
   `GetResourceOauth2Token` to that workload, token vault and CRM provider ARN.
   Do not grant access to SharePoint providers. The SDK uses the configured provider ARN region.
4. Build from the repository root:
   `docker build --platform linux/arm64 -f servers/crm_mcp/Dockerfile -t crm-mcp .`
   Deploy its own image/Runtime and configure the variables above. Restrict Runtime
   invocation to the Gateway role and use the repository's private-network controls.
5. Add Gateway target **`crm-application`**. Allow `x-mcp-caller-assertion` at both
   target metadata and Runtime header configuration; deploy the updated request
   interceptor. It forwards the original signed caller JWT for the exact CRM tool.
6. Configure inbound Entra API v2 application role
   **`MCP.CRM.Case.Summary.Update`** with Application membership, assign only
   approved client service principals, and include the `idtyp` optional access-token
   claim. Gateway validates issuer/audience/client and enforces the CRM Cedar policy
   in **ENFORCE** mode. An app-only token has roles and no delegated `scp`.
   Existing `MCP.CRM.Admin` user role does not authorize this operation.
7. Synchronize Gateway tools and verify success plus unknown caller/case, delegated
   token, wrong audience, provider isolation and direct Runtime invocation denials.

ClickOps is the current deployment path. The new policy/interceptor source is
provided, but existing Terraform environment examples do not provision/enable the
CRM provider, workload, role assignment or Runtime. Do not assume a Terraform
apply deploys this server. Configure all steps above before enabling the target.

## Write behavior and operations

The server validates inputs and the signed caller before requesting a downstream
token, then sends one `PATCH /api/data/v9.2/incidents(<case_id>)` with only the
configured summary column. `If-Match: *` prevents upsert, **not concurrent writes**:
this slice uses last-write-wins. The CRM owner must accept that policy before
release; otherwise add an expected-version contract before enabling writes.

Only HTTP 204 produces success, returning status and case ID. Redirects are not
followed. There are no automatic write retries. A timeout or connection failure
has an uncertain outcome: reconcile through CRM auditing before a deliberate
retry, particularly where plug-ins/flows run on update. Missing/closed cases,
permissions, business rules, throttling and token failures propagate as errors.
No case body or summary is returned/logged; success audit records caller and case
identifiers. Gateway/Runtime request-body tracing must also remain disabled.
Application rollback does not undo CRM writes; the CRM owner owns correction.

Live Entra/Identity/Dataverse integration, credential rotation, record/column
permissions, automation effects and operational alerts remain release gates.

References: [Dataverse S2S authentication](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/use-single-tenant-server-server-authentication),
[Web API update semantics](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/update-delete-entities-using-web-api).
