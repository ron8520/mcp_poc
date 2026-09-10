# ADR 0012: AgentCore Identity for Delegated and M2M Lanes

Date: 2026-08-25

Status: Accepted for PoC validation

This ADR supersedes ADR 0011. It preserves ADR 0011's current-PoC baseline,
trust-domain Runtime sizing, default-deny resolver, and fail-closed provider
routing, while making AgentCore Identity the target outbound token broker for
both delegated/OBO and autonomous M2M lanes.

ADR 0013 adds the staged per-workload Entra app-only catalog, one-environment
TFE state, interim provider-binding handoff, bounded JSON configuration, and
BAU/revocation sequence. It supersedes only the delivery details in this ADR;
the lane-selection, identity, provider-IAM and downstream-authorization
decisions remain authoritative here.

## Context

The MCP client type does not determine the downstream identity mode. Claude
Code is only one delegated-client example. An employee can also use a web AI
application, internal copilot, or another approved MCP client. If the downstream
operation must respect that employee's permissions, the request must preserve
the employee as the security subject.

Conversely, a scheduler, workflow engine, daemon, or service integration can run
without an employee security subject. Those operations use an application
identity and an OAuth client-credentials grant when the downstream system
supports OAuth M2M.

This distinction matters because an application token cannot ask SharePoint,
CRM, or another downstream system to evaluate an absent employee's native ACL.
If an employee-facing AI application silently changes a delegated request into
M2M, it can bypass the employee's downstream denial whenever the application
identity has broader privileges.

AWS documents that AgentCore Identity can obtain OAuth tokens for both
user-delegated and M2M access. It also supports OBO token exchange for MCP
servers and `CLIENT_CREDENTIALS` or `TOKEN_EXCHANGE` authorization on Gateway
targets. AWS separately states that access to credential providers must be
scoped with workload IAM; AgentCore Identity does not automatically bind every
workload identity to only the intended provider in the same account.

The current repository PoC predates this target. It has two fixed SharePoint
Runtime lanes, Gateway-to-Runtime IAM/SigV4, a delegated assertion-copy Lambda,
Runtime-side MSAL OBO, direct Runtime-side Graph client credentials, and gated
app-only Gateway ingress. This ADR does not describe those native Identity
paths as implemented.

## Decision

### Select a lane by security subject

Use the downstream security subject, not the client product name, to select the
lane:

- **Delegated/OBO lane:** a signed-in employee is the security subject and the
  downstream service must apply that employee's permissions.
- **Autonomous M2M lane:** no employee is the security subject; a narrowly
  approved workflow, scheduler, daemon, or service principal performs a fixed
  business operation with application permissions.

A user-facing AI application can use the delegated lane. A background process
can use the M2M lane. Merely running work asynchronously does not make it M2M:
if the operation still depends on the initiating employee's permissions, it
must preserve delegated identity or use a separately approved, narrowly scoped
job authorization model.

The caller must never select a credential mode, provider alias, provider ARN,
client ID, secret, or hidden authentication field through MCP input. Gateway
JWT validation, Entra grant-compatible claims, exact Cedar actions, target
routing, trusted caller context, and Runtime configuration determine the lane.

### Use AgentCore Identity for both target lane types

AgentCore Identity is the target outbound OAuth broker for both lane types. The
flows remain separate:

```text
Delegated employee flow
  Employee via AI app/client
    -> Entra delegated Token A, audience = Gateway
    -> Gateway CUSTOM_JWT + Cedar
    -> AgentCore Identity OBO
    -> Token B, audience = delegated Runtime
    -> delegated Runtime JWT validation
    -> AgentCore Identity OBO
    -> Token C, audience = downstream API
    -> downstream user ACL

Autonomous M2M flow
  Approved workflow/scheduler/daemon
    -> Entra application Token A, audience = Gateway
    -> Gateway CUSTOM_JWT + Cedar
    -> application Runtime trust domain
    -> AgentCore Identity M2M / client_credentials
    -> downstream application token
    -> downstream application grants
```

For the delegated target, Gateway target authorization uses AgentCore Identity
`TOKEN_EXCHANGE` to obtain the Runtime-audience Token B. This target invocation
therefore uses OAuth/JWT rather than the current PoC's IAM/SigV4 plus copied
assertion. The Runtime then uses AgentCore Identity OBO again for the final
downstream audience.

For the M2M target, Gateway may continue to invoke the application Runtime with
IAM/SigV4 while the Runtime uses AgentCore Identity `M2M` to obtain the
downstream token. When one trust-domain Runtime serves multiple approved
application callers, it revalidates trusted signed caller context before its
default-deny resolver selects an allowed provider profile. The complete
Gateway-SigV4-plus-caller-context composition remains a PoC validation gate.

Microsoft Entra ID or the applicable external IdP remains the token issuer.
AgentCore Identity brokers tokens and protects long-lived provider credentials;
it does not decide whether an employee may read a SharePoint site or whether an
application may use a CRM record. The downstream API remains the final
authorization boundary.

### Keep identity and credential blast radii separate

Do not implement one universal Runtime that can dynamically switch between all
delegated and M2M credentials. Keep separate targets and Runtime/workload
identities where downstream identity semantics or approved trust domains differ.
Multiple lanes for the same MCP server reuse the same immutable service image.

Every Runtime/workload IAM role must allow only the AgentCore Identity
credential-provider ARNs approved for that lane or trust domain:

- a delegated Runtime can access only its approved OBO providers;
- an application Runtime can access only its approved M2M providers; and
- cross-lane and cross-trust-domain provider access is explicitly denied and
  negatively tested.

Do not grant `bedrock-agentcore:GetResourceOauth2Token` against wildcard provider
resources. A successful Cedar decision does not grant access to a credential
provider, and access to a provider does not grant access to every downstream
resource.

### Generalize routing without changing server contracts

The application resolver key is generalized for future downstream servers:

```text
validated caller client ID
+ exact target-qualified action
+ server-owned downstream resource key
+ environment
```

For the current SharePoint tools, the server-owned downstream resource key is
the existing `site_id`, passed to Graph unchanged. CRM or another MCP server
may use its own reviewed tenant, workspace, account, or resource identifier.
This ADR does not add a generic `resource_ref` to the SharePoint public tool
contract.

Callers cannot supply provider-selection fields. Missing mappings, invalid
caller context, unavailable configuration, unavailable providers, or trust-
domain mismatches fail closed without exposing provider or credential details.

### Apply the pattern only where it fits

Each future downstream MCP server chooses zero, one, or both identity lanes
based on supported protocols and business authorization semantics:

- use delegated/OBO only when a user remains the security subject and the
  downstream IdP/API supports the required delegation exchange;
- use M2M only for approved autonomous operations with application permissions;
- use AWS IAM for AWS-native service authorization where IAM is the correct
  downstream mechanism; and
- use no outbound credential for approved public-documentation targets.

AgentCore Identity is therefore the shared target broker for OAuth-based
delegated and M2M lanes, not a requirement to force every downstream target onto
OAuth.

## Consequences

Positive:

- Employee-facing AI applications cannot gain application-level downstream
  access merely because they are applications.
- Background workloads have an explicit M2M path without inventing a fake user.
- Runtime code no longer needs to hold long-lived downstream OAuth secrets in
  the target design.
- The same lane rule applies to SharePoint, CRM, internal APIs, and future MCP
  servers without creating two lanes for every server by default.
- Workload IAM and provider-ARN scoping create auditable credential blast-radius
  boundaries.

Tradeoffs and risks:

- Native OBO, Runtime audience validation, Identity M2M, caller-context
  propagation, and provider IAM controls still require non-production proof.
- M2M represents the application, not an employee. A broad downstream
  application grant remains broad even when Gateway policy is narrow.
- A downstream API without OBO support cannot provide native user-level
  authorization through this pattern.
- Provider profiles, workload identities, resolver mappings, rotation, quota,
  rollback, and audit evidence become platform operations responsibilities.

## Validation gates

1. Keep the current fixed SharePoint lanes and gated app-only ingress until the
   target gates pass.
2. Validate Gateway `TOKEN_EXCHANGE` from the Gateway audience to the delegated
   Runtime audience and prove the Runtime rejects Token A and Graph Token C.
3. Validate Runtime AgentCore Identity OBO from Token B to a real delegated
   downstream token and prove native user denial for an unauthorized employee.
4. Validate Runtime AgentCore Identity `M2M` against a lane-scoped Entra OAuth
   provider and prove no user claim is invented or required.
5. Prove an employee delegated token cannot invoke an M2M target/action and an
   application token cannot invoke a delegated target/action.
6. Prove Runtime/workload IAM denies cross-lane, cross-server, wildcard, and
   cross-trust-domain credential-provider access.
7. Validate the trusted app-only caller-context path, resolver hit/miss,
   immutable mapping version, unavailable-provider behavior, and no provider
   disclosure.
8. Validate a background workflow only against its approved downstream
   resources; for SharePoint, prove `Sites.Selected` denies an ungranted site.
9. For the next downstream server, record whether it needs delegated, M2M,
   native IAM, or no outbound credential before creating a Runtime lane.

## References

- [AgentCore Identity OAuth tokens for user-delegated and M2M access](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-authentication.html)
- [AgentCore Identity OBO token exchange](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html)
- [Gateway target authorization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-building-adding-targets-authorization.html)
- [Scope credential-provider access by workload identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/scope-credential-provider-access.html)
- [AgentCore Runtime security best practices](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html)
- [Microsoft delegated and application permissions](https://learn.microsoft.com/en-us/entra/identity-platform/permissions-consent-overview)
- [Microsoft OBO](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Microsoft selected permissions](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
