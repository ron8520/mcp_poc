# ADR 0014: Phase-One CRM Case Field Update Through App-Only MCP

Date: 2026-09-27

Status: Accepted for PoC validation

ADR 0015 concretizes the CRM product and single case-summary update contract
while retaining this ADR's phase-one boundary and acceptance-gate decisions.

## Context

The first delivery previously focused on SharePoint. The requested first-stage
scope now also includes a CRM MCP server with one operation: update one field
on a CRM case, using application-only identity. CRM remains a separate server
boundary as established in ADR 0007. ADR 0012's separation of caller identity,
AWS workload identity and downstream credentials remains in force.

The CRM product, API, selected case field, allowed values, record scope and
credential method have not yet been supplied. This decision defines the
architecture and release boundary; it does not imply a working CRM integration.

## Decision

- Phase one includes SharePoint and CRM behind the same AgentCore Gateway.
  Internal software and public documentation targets remain outside this slice.
- CRM has its own MCP service image, Gateway target and application Runtime
  lane (`crm-application`). It does not run inside the SharePoint service or
  reuse SharePoint credentials/provider access. No CRM delegated lane is
  included in phase one.
- Expose exactly one CRM business operation: set the approved field on one
  authorized case to an allowed value. The case reference and value are the
  necessary business inputs; the approved field is fixed in reviewed service
  configuration. Do not expose arbitrary field names, generic patches, bulk
  updates, case creation/deletion or general CRM read/search operations.
  Confirm the final input contract after the field/API are known.
- The calling application obtains an Entra access token for the shared Gateway.
  Gateway validates that application and authorizes the exact CRM update
  operation. Signed caller context reaches the CRM Runtime through the trusted
  Gateway path and is revalidated there.
- CRM Runtime checks caller, environment, allowed case scope, approved field
  and permitted value before selecting the configured downstream identity.
  The caller cannot choose credential providers or downstream credentials.
- The target obtains a separate CRM application token through a lane-scoped
  AgentCore Identity M2M provider. The CRM product's supported authorization
  server issues this token. It is not assumed to be Entra, Microsoft Graph or
  the same audience as the Gateway. Broker/provider compatibility and the
  credential method are explicit implementation gates; unsupported integration
  requires a reviewed decision, not an implicit authentication fallback.
- CRM applies its own service-account/application record and field permissions.
  SharePoint's `Sites.Selected` does not apply to CRM. Employee ACLs are not
  inherited by this application-only operation.
- Return only an acknowledgement and necessary case/update identifiers. Do not
  return or log a full case, sensitive field values or credentials. Audit caller,
  operation, authorized record reference, outcome and correlation metadata.

## Consequences

CRM and SharePoint can be patched, disabled and released independently. Separate
Runtime roles and provider allowlists limit a compromise from crossing between
the systems. The same caller may be granted either integration or both, but a
SharePoint permission never implies CRM permission.

The CRM owner must approve the case population, field, value constraints and
any workflow side effects. A field update may trigger CRM automations, so
setting an identical value cannot be presumed harmless to replay. Timeout after
submission has an uncertain outcome; do not blindly retry. Agree verification,
concurrency and correction procedures with the CRM owner without introducing
a second public MCP operation by default.

## Phase-one acceptance gates

1. Confirm CRM product/API and authorization server, supported M2M provider,
   environment, approved field/value contract, application permissions and
   authorized case scope.
2. Implement the one-operation CRM service and its separate image, target,
   Runtime, caller policy, signed-context propagation and credential boundary.
   These resources are not enabled by this documentation change.
3. Demonstrate one authorized update and denials for an unknown application,
   wrong environment/case, disallowed value/field and direct Runtime bypass.
4. Demonstrate that CRM cannot obtain SharePoint credentials and vice versa,
   and that SharePoint tool roles do not authorize the CRM update.
5. Confirm audit minimization, throttling/timeout behavior, update side effects,
   credential rotation, independent disable/rollback and data-owner correction.

## References

- [ADR 0007: service and credential-mode boundaries](0007-identity-lanes-by-downstream-credential-mode.md)
- [ADR 0012: delegated and M2M credential brokering](0012-agentcore-identity-for-delegated-and-m2m-lanes.md)
- [Phase-one internal architecture review](../architecture/enterprise-mcp-platform-internal-review.md)
