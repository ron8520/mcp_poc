# Gateway

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
