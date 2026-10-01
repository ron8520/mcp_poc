# ADR 0015: Dynamics 365 case summary through app-only CRM MCP

- Date: 2026-09-28
- Status: Accepted for PoC validation

## Context

ADR 0014 included a separate CRM service in phase one without choosing the CRM.
The business system is now confirmed as Dynamics 365/Dataverse. Only a case's
summary may be changed. Its actual text column logical name remains deployment
configuration; `new_summary` is a hypothetical custom column, not a standard field.

## Decision

- Implement a separate CRM image/server and application Runtime with the single
  tool `crm_update_case_summary(case_id, summary)`. Case ID is the `incidentid`
  GUID. Require nonempty text bounded by configured column length. No dynamic
  field names, user-action updates, generic patches or bulk operations.
- Authenticate callers using signed Entra v2 app-only tokens for the Gateway API.
  Runtime revalidates the token, requires `MCP.CRM.Case.Summary.Update`, and checks
  an explicit configured caller-to-case GUID map. Ordinary tool arguments cannot
  choose caller identity. Gateway forwards the signed token only to the CRM tool.
- Use a separate downstream Entra app and Dataverse application user, per
  environment, with a least-privilege Case security role. The CRM Runtime obtains
  a Dataverse-audience token through its dedicated AgentCore Identity M2M provider
  and workload/IAM boundary. No Graph token, delegated CRM flow or MSAL fallback.
- Send one PATCH to the configured Dataverse environment's `incidents` resource,
  changing only the configured summary column. `If-Match: *` prevents accidental
  creation. Return only status/case ID after HTTP 204; do not follow redirects or
  automatically retry writes. Do not log the summary or full downstream response.
- The PoC write contract is last-write-wins, not optimistic concurrency. The CRM
  owner must accept it before enabling the target, or the implementation must
  add an expected-version contract. Reconcile uncertain writes before retries.
- Continue ClickOps deployment. Existing Terraform environments do not yet
  provision CRM identity/Runtime resources. Server source, image definition,
  interceptor support and Cedar policy do not prove a deployed working path.

## Consequences

CRM permissions and credential rotation are independent of SharePoint and the
Gateway caller app. Application-user permissions remain the downstream record
boundary; field security should constrain credentials where the column supports
it. Code restrictions alone do not constrain use of stolen CRM credentials.

The initial explicit case map is intentionally small and has no wildcard. Larger
case populations require an approved authorization design rather than broadening
the PoC map implicitly. Public-cloud Dataverse origins are supported initially.

Release gates include the actual writable field/length, CRM record and field
permissions, Identity/Entra M2M compatibility, Gateway-only invocation and
ENFORCE policy, successful/denied end-to-end calls, case business rules, concurrent
writers, update-triggered automation, rotation/disable and data correction.

References: [Dataverse S2S authentication](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/use-single-tenant-server-server-authentication),
[Case table](https://learn.microsoft.com/en-us/dynamics365/developer/reference/entities/incident),
[update semantics](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/update-delete-entities-using-web-api),
[AgentCore M2M API](https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_GetResourceOauth2Token.html).
