# Gateway

AgentCore Gateway itself is not implemented as Python code in this repo.

The Gateway is deployed by Terraform:

```text
infra/agentcore_gateway.tf
```

This folder contains optional Gateway-adjacent code only:

```text
optional_claims_interceptor_lambda.py
```

That file is a Lambda interceptor example. Use it only if the runtime needs
sanitized caller context headers after Gateway has already validated the Entra
JWT. It is not the Gateway and it does not replace Gateway policy.

Inbound MCP callers, including Claude Code, authenticate with an Entra bearer
token. AWS IAM roles are used by Gateway and Runtime after the JWT is accepted;
they are not the caller credential sent by Claude Code.
