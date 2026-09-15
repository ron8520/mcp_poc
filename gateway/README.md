# Gateway (Current PoC)

AgentCore Gateway itself is not implemented as Python code in this repo.

The Gateway is deployed by Terraform:

```text
infra/agentcore_gateway.tf
```

This folder contains the request interceptor used by the SharePoint OBO lane:

```text
obo_assertion_interceptor.py
```

After Gateway validates the Entra JWT, the interceptor copies the raw bearer
token to `x-mcp-user-assertion` only when the selected action starts with
`sharepoint-delegated___`. The header is allowlisted only on the delegated
target and Runtime. It is an OBO credential assertion, not an authoritative
identity claim or an MCP tool argument. Cedar remains the caller/tool
authorization boundary.

Inbound MCP callers, including Claude Code, authenticate with an Entra bearer
token. AWS IAM roles are used by Gateway and Runtime after the JWT is accepted;
they are not the caller credential sent by Claude Code.

The interceptor intentionally does not log the event or token and returns a
401 without invoking Runtime if a delegated-lane call has no bearer assertion.

## Target identity-routing gate

The default deployment has no live native outbound AgentCore Identity provider
registration. The opt-in staged branch does contain the explicit caller-context
interceptor, default-deny resolver and bounded `APP_ONLY_MAPPING_JSON` mapping;
`app_only_provider_bindings` names an already-registered provider ARN and does
not provision it. There is no Configuration Bundle delivery or `resource_ref` in
the SharePoint contract. App-only Gateway ingress is gated off. The accepted
target uses AgentCore Identity for delegated OBO and autonomous M2M. For
app-only caller context, it prefers a request interceptor that copies the
original signed caller JWT to `x-mcp-caller-assertion` without token exchange,
secret lookup, or provider selection. A trust-domain Runtime must accept only
Gateway SigV4 ingress and revalidate `iss`, Gateway `aud`, `exp`, `tid`, v2
`azp` or v1 `appid`, and `roles` before requesting an Identity M2M token.

The catalog creates caller and downstream Entra registrations, service
principals and role/permission assignments, but it does not create the caller's
password, certificate or federated credential. The caller authentication method
and downstream provider credential method remain approved implementation gates;
Entra/AD synchronization alone does not make the caller able to obtain a token.

The target delegated flow uses Gateway `TOKEN_EXCHANGE` for Runtime Token B and
Runtime OBO for downstream Token C. It replaces the current assertion-copy/MSAL
path only after non-production validation. The official AWS documentation does
not provide the complete native no-code app-only caller-context composition,
and it remains unverified; `JWT_PASSTHROUGH` is not the default. See
[`docs/architecture/sharepoint-identity-routing.md`](../../../docs/architecture/sharepoint-identity-routing.md).
