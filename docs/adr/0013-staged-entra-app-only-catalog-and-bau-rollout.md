# ADR 0013: Staged Entra App-Only Catalog and BAU Rollout

Date: 2026-09-08

Status: Accepted for PoC validation

This ADR adds the staged app-only implementation and operating model. It
clarifies the configuration-delivery and onboarding details in ADR 0012; the
ADR 0012 lane-selection, delegated/OBO, M2M, and downstream-authorization
decisions remain in force.

## Context

Cyber requires each approved AI application or agent to have an independently
auditable Entra identity for its MCP caller path and its downstream application
path. A sensitivity-group permission model is not part of this design. The
caller identity and downstream identity remain separate so an AI application
cannot use its Gateway credential to call Microsoft Graph directly.

The deployment must remain operable for both `nonprod` and `prod`. The selected
shape is one Terraform Enterprise (TFE) workspace and state per environment for
the Enterprise MCP API, caller/downstream applications, AgentCore Gateway and
AgentCore Runtime. The repository now contains the composed `deployment/` root,
which directly calls `module.entra -> ../identity/entra` and
`module.platform -> ../infra` and wires the identity outputs into the platform
module. The code and service images remain in this repository initially and may
be split into separate repositories later without changing the identity
contract.

The current delegated path remains the MSAL assertion-copy/OBO PoC. Native
two-hop AgentCore Identity OBO is a separate deferred migration and is not a
gate for the app-only work. The current app-only Gateway ingress remains
disabled until the app-only caller, Runtime, provider and downstream grants have
passed non-production validation.

AgentCore provider registration is not yet resolved. Entra ID, Terraform and
the enterprise AD sync boundary are confirmed, but the caller application
authentication method and downstream provider credential method (federation,
certificate or secret) are not selected. A Terraform input that names an
already-registered provider is therefore an explicit interim handoff, not proof
of native provider provisioning or live token exchange. Entra/AD synchronization
does not provision a caller password, certificate or federated credential.

## Decision

### 1. Keep one environment deployment state

Use one TFE workspace/state per environment for the Entra API and app catalog,
AgentCore Gateway, AgentCore Runtime and their wiring. Keep `nonprod` and `prod`
as separate environments with separate audiences, applications, state and
approvals. The composed `deployment/` root calls:

```text
module.entra    -> ../identity/entra
module.platform -> ../infra
```

The composed root passes identity outputs, including caller client IDs and
audience/discovery values, into the platform module. An optional lane image
override is allowed for validation; the default remains the service image
selected by the platform configuration. The TFE admin repository owns workspace
creation, backend configuration and execution controls.

### 2. Use a stable workload-keyed app-only catalog

Represent each approved autonomous workload with a stable workload name. Each
entry contains at least:

```text
app_only_apps[stable_workload_name]
  owner
  grants
    site_id -> exact MCP tools/actions
```

The catalog creates two separate Entra applications and service principals per
workload/environment where SharePoint app-only access is enabled:

1. a caller application and service principal that receives only the approved
   Enterprise MCP API application role; and
2. a downstream SharePoint application and service principal that receives the
   reviewed Microsoft Graph application permission and is the subject of the
   selected-site grant.

The `grants` map is an explicit site-to-tool allowlist. It is not a replacement
for Gateway Cedar or SharePoint authorization: Cedar still authorizes the exact
target-qualified MCP action, and SharePoint still enforces `Sites.Selected`.
The caller cannot submit a provider, client ID, secret, authentication mode or
alternate resource selector as MCP input.

App-only grants are assigned directly to the catalog entry's service principal;
there is no sensitivity-group dependency. Delegated user groups and their
employee app roles remain separate and continue to represent delegated
capability, not SharePoint site membership. Terraform does not create the
caller application's password, certificate or federated credential, so the
caller cannot obtain an app-only token until its approved authentication method
is provisioned.

### 3. Use a shared Runtime with an explicit app-only adapter

The default remains one application Runtime per approved downstream/trust-domain
isolation boundary, not one Runtime per caller. Multiple workload entries may
reuse the immutable service image. The app-only PoC adapter is explicit about
its mode and identity calls:

```text
GRAPH_AUTH_MODE=agentcore_m2m
GetWorkloadAccessToken(workloadName)
GetResourceOauth2Token(M2M)
-> per-request downstream Graph application token
```

The trusted app-only request interceptor copies the signed caller JWT into the
dedicated caller-context header. The Runtime revalidates the signed app token
(including the version-appropriate application identity claims and `idtyp=app`)
and checks the exact catalog key, site and tool before requesting a token. Local
adapter tests do not prove a deployed AgentCore, Entra or Graph exchange.

A shared Runtime's IAM role has the union of the provider ARNs it is permitted
to access. The catalog resolver provides logical per-workload routing and audit,
not hard infrastructure isolation: a compromise of that Runtime could still
reach any provider covered by its IAM policy. If this blast radius is not
acceptable, use a separate Runtime and IAM role for the stronger isolation
boundary.

### 4. Treat provider registration and downstream grants as explicit gates

The interim `app_only_provider_bindings` input maps each logical downstream
application to an already-registered AgentCore Identity provider ARN. It is an
explicit PoC handoff and must not be documented as native provider creation.
The downstream provider credential method and registration automation remain
unresolved. Do not place provider secrets in tfvars, Terraform state, Runtime
environment variables or logs.

Microsoft Graph `Sites.Selected` admin consent and the explicit site permission
grant remain a separate downstream-owner/admin operation. Site-grant
automation, provider registration, and live M2M token validation are unfinished
and must produce evidence before app-only ingress is enabled.

### 5. Start with bounded environment configuration

The first PoC delivery uses the small immutable schema-1
`APP_ONLY_MAPPING_JSON` catalog/binding configuration in the Runtime
environment. Terraform enforces the implementation's 5000-character limit.
The value is versioned with the reviewed deployment input and has no dynamic
configuration service, generic policy engine, weighted rollout, or
caller-controlled rule evaluation.

A pinned private S3 snapshot may be evaluated for BAU when the environment
configuration becomes too large. An AgentCore Configuration Bundle is optional
and deferred; it is not a prerequisite or current implementation claim.

### 6. Operate onboarding and revocation as separate gates

The normal BAU sequence is:

```text
onboard disabled
  -> create/update catalog identities and reviewed grants
  -> validate caller, exact tool, provider and downstream site permissions
  -> enable the caller/ingress only after evidence and approval
```

For revocation, first disable the caller/ingress and revoke the native
downstream grants or provider binding, then invalidate or wait out old sessions
and tokens according to the participating service. A code/image rollback is a
separate operation; it does not by itself revoke Entra, AgentCore or Graph
permissions. Record both permission rollback and code rollback independently.

## Consequences

Positive:

- Each app-only workload has an independent caller identity, downstream
  identity, owner and site-to-tool grant for audit and revocation.
- One environment state and a small catalog keep normal onboarding bounded.
- Existing delegated user groups and native SharePoint ACLs remain untouched.
- App-only identity work can be validated without changing the current OBO path.

Tradeoffs and open gates:

- Shared Runtime IAM has a union-of-provider blast radius; it is not per-app
  hard isolation.
- Provider credential registration method and automation are unresolved.
- Sites.Selected grant automation, live AgentCore M2M and live downstream tests
  remain outstanding.
- A separate Runtime/IAM boundary is required if the union blast radius is not
  acceptable.

## Validation gates

1. Plan both environment configurations from one composed root and verify that
   each environment has independent TFE state and outputs.
2. Verify a catalog entry creates a caller app/service principal and a separate
   SharePoint app/service principal, with no app-only sensitivity-group grant;
   verify that it does not silently create a caller credential.
3. Verify the caller app role, exact Cedar action, site-to-tool grant and
   downstream `Sites.Selected` permission are independently visible.
4. Run the app-only adapter's positive, missing-catalog, wrong-workload,
   wrong-site, wrong-tool, wrong-role, wrong-tenant, wrong-audience, expired and
   non-application-token tests. Provider and configuration failures must
   propagate without a default identity or fallback provider.
5. Validate the trusted caller header, per-request AgentCore M2M token path,
   provider ARN binding and Graph application token in non-production. Validate
   the approved caller authentication method separately. Do not treat unit
   tests or Terraform plans as live token evidence.
6. Prove the shared Runtime IAM union and document whether its blast radius is
   accepted. If not accepted, split the Runtime/IAM boundary before enabling.
7. Complete admin consent and explicit SharePoint site grants, then validate
   denial for an ungranted site and exact site-to-tool combinations.
8. Enable app-only ingress only after Cedar is enforced and the preceding gates
   are approved. Keep delegated OBO migration as a separate work item.

## References

- [ADR 0012: AgentCore Identity for Delegated and M2M Lanes](0012-agentcore-identity-for-delegated-and-m2m-lanes.md)
- [Downstream identity routing](../architecture/sharepoint-identity-routing.md)
- [Entra identity Terraform example](../../examples/enterprise_mcp_platform/identity/entra/README.md)
- [Infrastructure Terraform example](../../examples/enterprise_mcp_platform/infra/README.md)
- [Composed deployment root](../../examples/enterprise_mcp_platform/deployment/README.md)
- [Direct Cedar policy](../../examples/enterprise_mcp_platform/policy/README.md)
