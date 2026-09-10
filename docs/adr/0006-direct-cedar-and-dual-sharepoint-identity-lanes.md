# ADR 0006: Direct Cedar and Dual SharePoint Identity Lanes

Date: 2026-07-29

Status: Accepted for implementation

ADR 0010 supersedes the `sharepoint-user` / `sharepoint-automation` names and
the multi-tool write contract. The direct Cedar, separate downstream credential
modes, OBO, application identity, and shared-image decisions remain in force.
ADR 0012 supersedes ADR 0011's target identity-routing path. The current
repository PoC remains the two fixed lanes described here; target AgentCore
Identity OBO/M2M providers and resolver behavior are not implemented.

## Context

The previous policy layout used `tool_allowlist.yaml` as a human-maintained
model, generated a Runtime JSON copy, and planned to translate the same source
into Gateway Cedar. That created three representations of one decision and two
authorization engines that could drift during change and deployment.

SharePoint also has two materially different identity flows:

- an employee acting interactively through Claude Code, where Microsoft Graph
  must act on behalf of that employee; and
- a scheduled or background workload, where Graph uses an application identity
  with explicitly selected site grants.

Encoding every SharePoint site in MCP policy or creating one Entra group per
site would duplicate SharePoint's native authorization model and create a
high-maintenance entitlement system.

## Decision

Cedar files under `examples/enterprise_mcp_platform/policy/cedar/` are the only
MCP tool-authorization source.

- Delete the YAML model, JSON Schema, generated Runtime JSON, policy review
  JSON, and the translator/validator script.
- Do not package policy files in MCP server images.
- AgentCore Gateway evaluates Cedar as the sole tool authorization point.
- AgentCore create/update validation with `FAIL_ON_ANY_FINDINGS` is the
  authoritative Cedar syntax, semantic, and Gateway-schema validation.
- MCP servers continue to validate untrusted input and enforce operational
  write controls. This is safety validation, not a second caller/tool policy
  engine.

Use two SharePoint execution lanes behind the shared Gateway:

1. `sharepoint-user`
   - receives delegated user requests;
   - uses Microsoft Graph OBO;
   - relies on the employee's native SharePoint site/item permissions.
2. `sharepoint-automation`
   - receives scheduled and background requests;
   - uses a separate Graph application identity;
   - relies on Graph application permissions plus explicit
     `Sites.Selected` grants.

Both lanes build from the same SharePoint MCP source and immutable image, but
they are separate Gateway targets and Runtime deployments because their caller
grant types, downstream credential behavior, failure domain, and audit meaning
differ. Gateway invokes both Runtimes with the same IAM/SigV4 mechanism.

For the user lane, a Gateway request interceptor copies the already validated
caller token into a dedicated OBO assertion header. Only the
`sharepoint-user` target and Runtime allowlist that header. The automation lane
does not receive it. The assertion is never accepted as an ordinary tool
argument.

Cedar authorizes exact target-qualified MCP actions:

```text
sharepoint-user___sharepoint_get_file_text
sharepoint-automation___sharepoint_get_file_text
```

Human and automation app roles grant tool capability, not site membership.
Site A versus Site B/C/D remains a SharePoint or Graph authorization decision.

## Repository Layout

```text
examples/enterprise_mcp_platform/
  policy/
    README.md
    cedar/
      sharepoint-human.cedar
      sharepoint-automation.cedar
  servers/
    sharepoint_mcp/
  infra/
    agentcore_gateway.tf
    agentcore_runtime.tf
  pipelines/
    azure-devops/
      policy-ci.yml
```

Generated AgentCore schemas or translated artifacts are not committed. CI may
retain validation output as short-lived build evidence.

## Consequences

Positive:

- One reviewed authorization language is deployed and evaluated.
- Policy changes do not require rebuilding every MCP server image.
- Runtime code no longer parses a policy bundle or reimplements Gateway
  authorization.
- A large number of SharePoint sites does not create the same number of
  MCP-specific Entra groups or Cedar rules.
- Human activity is constrained and attributed by native SharePoint ACLs,
  while automation has an independently reviewable `Sites.Selected` boundary.

Tradeoffs:

- Gateway target names and Cedar action identifiers must change together.
- Human OBO and automation app-only lanes need separate deployment and token
  handling.
- The OBO interceptor receives sensitive request headers and therefore must not
  log its input or token.
- Cedar cannot prove SharePoint authorization; end-to-end tests must verify
  both Gateway denial and downstream denial.
- The exact AgentCore serialization of Entra claims into principal tags must be
  validated with real non-production tokens before `ENFORCE`.

## Operational Rollout

1. Create the two Gateway targets and Runtime deployments.
2. Wire the Cedar files directly to `aws_bedrockagentcore_policy` with
   `FAIL_ON_ANY_FINDINGS`.
3. Deploy to non-production with Gateway policy in `LOG_ONLY`.
4. Validate delegated calls and policy findings while app-only entry remains
   blocked by the transitional Gateway-wide scope requirement.
5. Atomically promote the policy engine to `ENFORCE` and remove the transitional
   Gateway-wide `mcp.invoke` scope requirement so app-only tokens can enter the
   automation lane without weakening the pre-Cedar deployment.
6. Test delegated and app-only read/write, missing roles, cross-lane calls,
   SharePoint ACL denial, and `Sites.Selected` denial after the enforcement
   cutover.
7. Apply the same reviewed policy and deployment process to production.

## Supersedes

This ADR supersedes the policy-source, generated-artifact, and Runtime
authorization portions of ADR 0002, ADR 0003, and ADR 0005. Their repository,
Azure DevOps, and branch-policy decisions otherwise remain in force.
