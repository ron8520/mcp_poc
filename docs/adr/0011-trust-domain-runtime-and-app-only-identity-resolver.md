# ADR 0011: Trust-Domain Runtime and App-Only Identity Resolver

Date: 2026-08-20

Status: Superseded by ADR 0012

ADR 0012 preserves this ADR's current-PoC baseline, trust-domain sizing, and
default-deny routing controls. It supersedes the target outbound-identity
decision by making AgentCore Identity the target OAuth broker for both
delegated/OBO and autonomous M2M lanes and by generalizing the resolver resource
key for future downstream MCP servers.

## Context

The current SharePoint PoC is implemented as two fixed Runtime lanes. Gateway
uses `CUSTOM_JWT`, Cedar authorizes the exact target-qualified action, and
Gateway invokes the delegated and application Runtimes with IAM/SigV4. A thin
request-interceptor Lambda copies the validated delegated bearer to
`x-mcp-user-assertion`; the delegated Runtime uses MSAL OBO and the application
Runtime uses `client_credentials`. App-only Gateway ingress is currently gated
off. This is the implementation baseline, not the target identity design.

The target design must support user-delegated OBO without treating a Gateway
assertion-copy Lambda or Runtime-side MSAL as the final OAuth boundary. It must
also avoid creating one application Runtime for every caller or provider while
preventing one universal Runtime from reaching every downstream provider.

The SharePoint upload contract remains deliberately small:

```text
sharepoint_upload_file(site_id, file_path, content)
```

`site_id` remains an existing downstream identifier. It is passed to Graph
unchanged. It is not translated to or replaced by `resource_ref`.

## Decision

### Current PoC boundary

The current code and Terraform remain the reference implementation until the
target gates below pass:

- Gateway validates the inbound Entra JWT with `CUSTOM_JWT`.
- Gateway invokes the two fixed SharePoint Runtime lanes with IAM/SigV4.
- The interceptor only copies the delegated inbound bearer to
  `x-mcp-user-assertion`; it does not exchange tokens or retrieve secrets.
- The delegated Runtime uses MSAL OBO for Microsoft Graph.
- The application Runtime uses Microsoft Graph client credentials.
- App-only Gateway ingress remains disabled during the current Cedar rollout.
- There is no resolver, native outbound AgentCore Identity provider, immutable
  mapping snapshot, Configuration Bundle, or `resource_ref` in the current
  implementation.

### Target delegated identity

The target delegated path uses two independent, audience-specific OBO hops:

```text
Token A: caller token, audience = AgentCore Gateway
  -> AgentCore Identity OBO
Token B: MCP Runtime token, audience = the receiving Runtime
  -> AgentCore Identity OBO
Token C: Microsoft Graph token, audience = Microsoft Graph
```

OBO applies only to a user-delegated assertion. App-only service-principal
access remains client credentials. The target path must not send a Gateway
token directly to Graph or a Graph token to the Runtime.

The current interceptor/MSAL path is replaced only after non-production proves
the Gateway target exchange, Runtime JWT audience, Entra parameters, IAM
permissions, provider configuration and live Graph access. Until then, all
documentation must label native OBO as target behavior.

The reviewed AWS samples demonstrate Microsoft Entra delegated OBO through a
Gateway and from an MCP Runtime. They are useful implementation references for
the two delegated hops, but they are not evidence for the app-only
caller-to-provider resolver or its SigV4-plus-assertion composition.

### Target app-only trust-domain routing

The target uses one application Runtime for each approved trust domain, not one
Runtime per caller or provider. Runtimes in the same domain reuse the same
immutable service image. A trust domain is an approved audit, IAM and
credential-isolation boundary; it is not a synonym for an individual caller.

Each trust-domain Runtime contains a thin resolver that can select among the
provider profiles approved for that domain. It must not become a universal
Runtime with access to every provider. A new Runtime is normally unnecessary
when onboarding another caller or provider within an existing domain; create
one only when a new isolation boundary is approved.

The exact resolver key is:

```text
validated caller client ID
+ target-qualified exact action
+ existing site_id
+ environment
```

The resolver must:

- use only the Runtime-revalidated caller assertion and the exact
  target-qualified action already authorized by Cedar;
- preserve `site_id` exactly as supplied and pass it unchanged to Graph;
- reject caller-supplied provider aliases, provider ARNs, Graph client IDs,
  client secrets, or hidden provider-selection fields;
- fail closed on a missing mapping, key mismatch, unavailable mapping snapshot,
  unavailable provider, or trust-domain mismatch; and
- avoid revealing provider names, ARNs, credentials or mapping details in
  errors.

The preferred PoC caller-context path is a request-interceptor Lambda that only
copies the original signed caller JWT to `x-mcp-caller-assertion`. It does not
exchange a token, retrieve a secret, or choose a provider. The Runtime accepts
only Gateway SigV4 ingress and revalidates `iss`, Gateway `aud`, `exp`, `tid`,
the version-appropriate `azp` or `appid`, and required `roles`. The official AWS
documentation does not provide native no-code composition for this complete
app-only caller context, and it remains unverified. `JWT_PASSTHROUGH` is
therefore not the default: the original token's
audience and any direct-Runtime interpretation would change the current policy
risk model.

### Layered authorization and delivery

- Gateway JWT validation and Cedar authorize the caller, exact tool and input.
- Runtime resolver safety checks and credential routing select only an approved
  provider profile within the trust domain.
- Microsoft Graph and SharePoint enforce the final delegated ACL or
  `Sites.Selected` application grant.
- Runtime IAM/workload identity may access only provider ARNs approved for its
  trust domain.
- Git and Terraform remain the source of truth. Publish an immutable,
  versioned mapping snapshot. An AgentCore Configuration Bundle is a delivery
  candidate only after validation and must use a static pinned version.
- Do not use weighted or A/B mapping for security decisions. Mapping snapshots
  require cache, rollback, kill-switch, drift-detection and audit controls.

AgentCore OAuth provider quota is currently documented as 50 resources per
account and Region, subject to adjustment. Provider and identity counts must be
managed by audit and isolation requirements, not caller count.

### Onboarding and BAU

Onboarding requires the caller app role, exact Cedar action, resolver mapping,
reviewed mapping version, non-production positive and negative tests, and a
production approval. Create a new Graph app/provider/Sites.Selected grant only
when a distinct downstream identity, permission or audit boundary requires it.
Create a new Runtime only when that provider cannot remain inside an existing
approved trust domain. Otherwise, add the caller or provider profile to the
existing trust-domain configuration without creating a Runtime.

## Consequences

Positive:

- Delegated token audiences are explicit at every receiving service.
- Runtime count follows approved isolation boundaries rather than caller or
  provider count.
- Provider selection is platform-controlled and default-deny.
- The minimal SharePoint tool contract is preserved.
- App-only remains distinct from user-delegated OBO.

Tradeoffs and risks:

- Native delegated OBO and the app-only caller-assertion composition remain
  unvalidated until the non-production gates pass.
- A shared trust-domain Runtime and provider profile still have a union-of-
  grants blast radius within that domain.
- Configuration snapshots, provider quotas, cache invalidation, rollback and
  drift detection become operational responsibilities.
- An app-only provider must not be granted to a caller merely because the
  caller can invoke an MCP tool; resolver mapping and Graph grants remain
  separate controls.

## Validation gates

1. Validate the current two-lane baseline and record its Gateway, IAM/SigV4,
   interceptor, MSAL and app-only-ingress state.
2. In non-production, validate Gateway-to-Runtime `TOKEN_EXCHANGE` with the
   receiving Runtime audience.
3. Validate Runtime-to-Graph OBO with a separate Graph audience and real
   delegated tenant credentials.
4. Validate Runtime JWT claim revalidation for app-only caller context and
   reject wrong issuer, audience, tenant, client, role and expiry.
5. Validate resolver hit, miss, mismatch, unavailable-snapshot and
   unavailable-provider behavior without provider leakage.
6. Validate that callers cannot select provider aliases, ARNs, client IDs or
   secrets and that `site_id` reaches Graph unchanged.
7. Validate trust-domain IAM boundaries, provider quota assumptions, immutable
   mapping pinning, cache rollback, kill switch, drift detection and audit
   evidence.
8. Validate the AgentCore managed MCP dialect separately: `2025-11-25` is the
   current released stable protocol; `2026-07-28` is an RC/target for the
   Python SDK `mcp==2.0.0`, and managed Gateway support remains unverified.

## Operations

Operate each mapping snapshot as a versioned, reviewable artifact. Record the
caller, exact action, site ID, environment, mapping version, decision, provider
result and correlation ID without recording tokens, secrets or provider
credentials. A kill switch must deny the affected mapping or trust domain
without creating a direct Runtime bypass. Rollback must pin the last known-good
snapshot and verify negative tests before re-enabling access.

## References

- [AWS OBO token exchange](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html)
- [AWS sample: Entra OBO through Gateway](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/8f929e64911e0beb6c7ee4b458d5506d94b973d9/01-features/05-authenticate-and-authorize/obo-training/3-examples/02-agent-via-gateway/entra/real-world)
- [AWS sample: Entra OBO MCP Runtime](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/8f929e64911e0beb6c7ee4b458d5506d94b973d9/06-workshops/03-AgentCore-identity/13-entra-obo-mcp-runtime)
- [AWS blog: extending MCP support for AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/extending-mcp-support-for-amazon-bedrock-agentcore-gateway-2/)
- [Gateway target authorization](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-building-adding-targets-authorization.html)
- [Gateway header propagation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-headers.html)
- [Gateway interceptors](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-interceptors.html)
- [AgentCore limits](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html)
- [Credential-provider least privilege](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/scope-credential-provider-access.html)
- [Configuration Bundles](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/configuration-bundles.html)
- [Microsoft OBO](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Microsoft access-token claims](https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference)
- [Microsoft Sites.Selected](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
- [MCP releases](https://github.com/modelcontextprotocol/modelcontextprotocol/releases)
