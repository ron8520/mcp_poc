# ADR 0004: Claude Code Uses Entra JWT for MCP and AWS IAM Only Server-Side

Date: 2026-07-06

Status: Accepted for PoC validation

ADR 0006 supersedes the Runtime policy reference below. Direct Cedar at Gateway
is the sole caller/tool authorization policy; Runtime resource policies remain
IAM-based and Runtime still performs input and execution-safety validation.

## Context

Claude Code runs from an internal developer laptop on the corporate network. The
network can reach AWS through the approved private connectivity path, but network
location is not the caller identity for MCP authorization.

The platform also uses AWS IAM roles for AWS services. That can make the Claude
Code path look like two identities are being combined, especially because Bedrock
model access may use IAM while MCP tool authorization uses Microsoft Entra ID.

## Decision

Claude Code calls MCP with a Microsoft Entra ID access token.

The Claude Code path is:

```text
Claude Code on internal laptop
  -> approved token helper requests delegated Entra token
  -> token audience is the Enterprise MCP API
  -> Claude Code sends HTTPS MCP request to the AWS-side MCP endpoint
  -> request includes Authorization: Bearer <Entra JWT>
  -> AgentCore Gateway validates JWT issuer, audience, client, scope, roles/groups
  -> Gateway policy authorizes the requested MCP tool
  -> Gateway invokes Runtime using its AWS IAM role
  -> Runtime uses its AWS IAM role for AWS services and approved credentials
```

In this repository, the AWS-side MCP endpoint is Amazon Bedrock AgentCore Gateway
configured with `CUSTOM_JWT`. A separate AWS API Gateway service is not part of
the current design unless a future ADR adds it.

AWS IAM is not used as the inbound MCP caller credential. IAM is used after the
request reaches AWS infrastructure:

- Gateway role invokes Runtime.
- Runtime role writes logs, emits metrics/traces, pulls images, and accesses
  approved AWS-side secrets or credentials.
- Any AWS-hosted Bedrock model path uses IAM separately from MCP authorization.
  If a future approved direct-Bedrock mode uses workstation AWS credentials, that
  credential is still not sent to the MCP Gateway.

Do not combine the Entra JWT and AWS IAM role into one token or one logical
authorization check. Entra answers who the MCP caller is and which MCP tools the
caller can use. IAM answers which AWS service-to-service actions are allowed.

## Consequences

- Gateway policy and runtime policy can reason about human/developer identity
  using Entra claims.
- Runtime resource policies stay IAM-based and can restrict invocation to the
  Gateway role.
- Claude Code configuration needs a supported way to attach the Entra bearer
  token to MCP requests.
- Token helper scripts must refresh Entra tokens securely and avoid storing
  bearer tokens in static configuration.
- AWS IAM permissions granted for Bedrock do not grant MCP tool access.
- Private network connectivity improves exposure control but does not replace
  JWT validation.

## Related Documents

- [README](/Users/ronruan/Desktop/mcp_poc/README.md)
- [Claude Code sequence (Mermaid source)](/Users/ronruan/Desktop/mcp_poc/docs/architecture/claude-code-sequence.mmd)
- [Claude Code sequence (editable draw.io)](/Users/ronruan/Desktop/mcp_poc/docs/architecture/claude-code-sequence.drawio)
- [Enterprise MCP platform diagram](/Users/ronruan/Desktop/mcp_poc/docs/architecture/enterprise-mcp-platform.mmd)
- [ADR 0001](/Users/ronruan/Desktop/mcp_poc/docs/adr/0001-agentcore-runtime-mcp-platform.md)
