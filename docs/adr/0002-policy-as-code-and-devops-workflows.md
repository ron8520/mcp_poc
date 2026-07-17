# ADR 0002: Policy As Code And DevOps Workflows

Date: 2026-07-05

Status: Superseded by ADR 0003

Superseded note: ADR 0003 replaces the GitHub Actions/future-repo split
assumption with an on-prem Azure DevOps Server pipeline model and a single
cloud-owned platform repo.

## Context

The platform needs a maintainable way to manage which Claude Code developers,
service agents, MCP servers, tools, and downstream resources are allowed. The
policy must be reviewable by humans, enforceable by Gateway and Runtime, and
testable in CI before deployment.

The repo also needs an enterprise-shaped CI/CD example for MCP server images and
policy changes. The current PoC is one folder, but future production ownership
will likely split policy, infrastructure, and MCP servers into separate repos.

## Decision

Use YAML as the human-maintained policy source:

```text
examples/enterprise_mcp_platform/policy/tool_allowlist.yaml
```

Validate that YAML with JSON Schema:

```text
examples/enterprise_mcp_platform/policy/tool_allowlist.schema.json
```

Generate normalized runtime JSON:

```text
examples/enterprise_mcp_platform/policy/generated/tool_allowlist.json
```

The runtime loads the generated JSON by default. This keeps runtime dependencies
simple while preserving YAML comments and readability for policy owners.

Add CI/CD examples under:

```text
examples/enterprise_mcp_platform/.github/workflows/
```

Those workflows are authored as if `examples/enterprise_mcp_platform` is a
future standalone repo root. If the PoC remains nested in a monorepo, DevOps
must copy or adapt the workflows into the real root `.github/workflows` folder.

Document future repository boundaries under:

```text
examples/enterprise_mcp_platform/repo_boundaries/
```

Keep Entra identity Terraform under:

```text
examples/enterprise_mcp_platform/identity/entra/
```

This represents a future identity-owned workspace. Its outputs feed the AWS
AgentCore Gateway JWT authorizer variables, but it should not be merged into
the AWS `infra/` root unless the same team owns both lifecycles.

## Consequences

Positive:

- Policy changes are reviewable in YAML.
- JSON Schema catches structural errors before merge.
- Embedded policy test cases catch authorization regressions.
- Runtime has a stable generated JSON artifact.
- MCP server CI can validate code, policy compatibility, and Docker builds.
- DevOps can split policy, infra, and server ownership later without changing
  the logical contracts.
- Identity ownership is explicit and separate from AWS infrastructure.

Tradeoffs:

- Policy changes must regenerate `policy/generated/tool_allowlist.json`.
- Gateway Cedar policy generation is still a future implementation step.
- The nested example workflows do not run from the current monorepo location
  unless copied to the actual GitHub Actions workflow root.

## Follow-Up Work

- Generate Gateway Cedar policies from the YAML policy matrix or maintain a
  reviewed Cedar policy beside the YAML.
- Add real image scanning, SBOM, signing, and central ECR publish gates.
- Wire workflow outputs into the real TFE/TFC deployment process.
- Add negative tests for each new write-capable tool before enabling it.
