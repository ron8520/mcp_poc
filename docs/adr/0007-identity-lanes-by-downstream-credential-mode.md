# ADR 0007: Identity Lanes by Downstream Credential Mode

Date: 2026-07-29

Status: Accepted

ADR 0010 renames user/automation lanes to delegated/application lanes and
replaces the SharePoint write contract with one fail-fast file-upload tool. The
rule that Runtime lanes follow downstream credential mode remains in force.
ADR 0011 clarifies the target exception: app-only Runtime sizing follows
approved trust-domain isolation rather than caller/provider count. This target
is accepted for PoC validation only; the current repository still has the two
fixed SharePoint lanes and app-only ingress remains gated.

ADR 0012 supersedes ADR 0011 and the target-only statement that Gateway invokes
every Runtime with IAM/SigV4. The current PoC remains unchanged; the target uses
AgentCore Identity for both delegated/OBO and autonomous M2M token acquisition.

## Context

SharePoint requires both interactive employee calls and scheduled/background
application calls. These flows use different Microsoft Graph credentials:
delegated OBO for employees and client credentials for automation.

The same question will recur for CRM and future MCP servers. Always deploying
two Runtimes per downstream system would create unnecessary cost and
operational objects. Combining materially different downstream identities in
one Runtime would weaken isolation and make incident response and audit meaning
ambiguous.

## Decision

Define deployment lanes by downstream credential semantics, not by a fixed
platform-wide count.

- Each downstream system keeps its own server source and image boundary.
- Multiple lanes for one service use the same immutable service image.
- Create a separate Runtime and Gateway target only when a distinct downstream
  identity mode or operational isolation requirement exists.
- All lanes use the same AgentCore Gateway `CUSTOM_JWT` entry point.
- Gateway invokes all MCP Runtime targets with its IAM role and SigV4.
- Cedar authorizes the exact target-qualified action for each lane.

SharePoint has two lanes:

1. `sharepoint-user` uses Graph OBO.
2. `sharepoint-automation` uses a dedicated Graph application identity and
   `Sites.Selected`.

For OBO, a Gateway request interceptor copies the Gateway-validated inbound
bearer token to `x-mcp-user-assertion` only for
`sharepoint-user___*` calls. The user target and Runtime are the only resources
that allowlist this header. Runtime uses the assertion with its confidential
Enterprise MCP API credential to request a delegated Graph token. It does not
use the Enterprise MCP access token directly against Graph.

CRM starts with one disabled `crm-automation` lane in the Terraform example.
When CRM tool contracts are approved:

- keep one Runtime if all approved operations use one CRM application identity;
- add `crm-user` from the same CRM image only if the CRM API supports and
  requires delegated/OBO user semantics; and
- keep the CRM image separate from the SharePoint image even though both use
  AgentCore Runtime and may share a platform base image.

## Consequences

Positive:

- Service code is built once and configured into the required identity lanes.
- Runtime count follows real security requirements instead of a universal
  two-per-service rule.
- A compromised automation credential is isolated from delegated user
  execution.
- Cedar actions, logs, alarms, rollback, and ownership remain lane-specific.
- CRM can begin with the simplest viable deployment and add a user lane without
  restructuring its source code.

Tradeoffs:

- Each additional lane creates another Runtime, target, IAM role, secret
  allowlist, alarm set, and cost unit.
- Environment configuration must keep target names, Cedar actions, auth mode,
  and downstream credentials aligned.
- The OBO interceptor handles a bearer assertion and needs strict no-token
  logging, a small allowlist, and negative tests.
- A downstream API that does not support OBO cannot gain user-level
  authorization merely by adding a user lane.

## Implementation

Terraform models one `mcp_servers` object per service and flattens its enabled
`lanes` into Runtime and Gateway target resources. SharePoint user and
automation lanes share one `image_uri`. The disabled CRM example declares only
an automation lane.

Runtime configuration selects `GRAPH_AUTH_MODE=obo` or
`GRAPH_AUTH_MODE=client_credentials`. Confidential-client values are retrieved
from lane-specific Secrets Manager ARNs; secret values are not Terraform
inputs.

## Relationship to Earlier Decisions

This ADR extends ADR 0006. It keeps the dual SharePoint decision and defines
when that pattern should or should not be repeated for CRM and future services.
