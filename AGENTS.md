# Agent Instructions for This Repository

These instructions apply to the whole repository.

## Project Context

This repository is a planning and proof-of-concept workspace for an enterprise
MCP platform on AWS.

The current target architecture is:

- one shared Amazon Bedrock AgentCore Gateway MCP endpoint
- one AgentCore Runtime per enabled downstream-identity lane; multiple lanes
  for one server reuse the same immutable service image
- target outbound OAuth uses AgentCore Identity for both delegated/OBO and
  autonomous M2M lanes, with separate workload identities and provider-ARN IAM
  boundaries; the default PoC uses Runtime MSAL/client credentials, with an
  opt-in per-app AgentCore Identity M2M adapter pending live validation
- lane selection follows the downstream security subject, not the client name:
  employee-facing AI apps use delegated identity when user ACLs must apply,
  while approved workflows with no employee subject use M2M
- SharePoint as the first enabled MCP server
- CRM, internal software, and future systems as separate MCP server boundaries
- Microsoft Entra ID JWTs for MCP caller identity
- AWS IAM kept separate for Bedrock model access
- Terraform for infrastructure
- one TFE workspace/state per environment, composed from
  `examples/enterprise_mcp_platform/deployment/` using `module.entra` and
  `module.platform`; see ADR 0013 for staged app-only rollout
- Sydney (`ap-southeast-2`) as the current AgentCore Gateway/Runtime deployment
  region; Melbourne (`ap-southeast-4`) remains gated on AWS service support
- target AWS account ID and existing network resources supplied by the central
  platform/TFE configuration
- AgentCore Gateway PrivateLink, private DNS, endpoint policy, and routing
  owned by the external network/platform account rather than this Terraform root
- no CloudFront or CDN-backed custom domain for the MCP path
- centrally owned MCP base images extended by each service image

Keep this architecture consistent across code, diagrams, ADRs, and README
content unless a new architecture decision explicitly changes it.

## Working Style

For any coding-related task, use the `karpathy-guidelines` skill before
writing, reviewing, debugging, refactoring, or modifying code.

Before changing files:

1. State the assumptions that matter.
2. Choose the simplest viable change.
3. Keep edits surgical and tied to the request.
4. Define how the change can be verified.
5. Do not rewrite unrelated files or clean up unrelated issues.

If the request is ambiguous, make a reasonable local assumption when the risk is
low. Ask only when the choice would change architecture, security posture, data
handling, or deployment behavior.

### Minimal error handling

Validate the inputs required by an explicit contract, then let configuration,
identity-provider, token, upstream, and downstream failures propagate to the
owning boundary. Do not add catch-all handlers, default identities or providers,
implicit mode switching, or fallback chains. Error handling must not log or
disclose secrets, tokens, provider credentials, or sensitive downstream data.

## Architecture Decision Records

Architecture changes must create a new ADR file under `docs/adr/`.

Do not append a new architecture decision to an existing ADR. Existing ADRs may
be edited only for small corrections, broken links, or clarifying wording that
does not change the decision.

Use this ADR naming pattern:

```text
docs/adr/NNNN-short-kebab-case-title.md
```

Examples:

```text
docs/adr/0001-agentcore-runtime-mcp-platform.md
docs/adr/0002-runtime-private-networking.md
```

When creating a new ADR:

1. Find the highest existing ADR number in `docs/adr/`.
2. Use the next number with four digits.
3. Write a new file for the decision.
4. Include at least: title, date, status, context, decision, consequences.
5. Link or summarize the decision from `README.md` when it changes the system
   shape, deployment path, security model, or operational ownership.

ADR status values should be plain and specific, such as:

- `Proposed`
- `Accepted for PoC validation`
- `Accepted`
- `Superseded by ADR NNNN`

If a new ADR supersedes an older decision, leave the old ADR in place and add a
short superseded note to the old ADR. Do not delete the history.

## Documentation Sync Rules

When architecture design changes, update all affected project docs in the same
change:

- `README.md`: current architecture, diagrams, repo layout, and how the system
  is meant to work.
- `END_GOAL.md`: the target outcome and success criteria.
- `WHAT_WE_HAVE_DONE.md`: completed decisions or implemented work.
- `IN_PROGRESS.md`: validation work, open decisions, and unfinished
  implementation tasks.
- `docs/architecture/*`: diagrams and sequences when flows or boundaries
  change.
- `docs/adr/NNNN-*.md`: a new numbered ADR for the architecture decision.

Do not let README describe one architecture while ADRs or progress files
describe another.

The Markdown architecture sources are authoritative. Do not create, regenerate,
or maintain `docs/architecture/enterprise-mcp-platform-internal-review.docx`.

## Diagram Style

Use straight connector segments in all diagrams. Do not use curved connectors.

- Prefer a single horizontal or vertical line for a direct connection.
- When a connection must branch, use a shared trunk with orthogonal branches
  and 90-degree turns.
- Keep every segment horizontal or vertical wherever possible, and minimize
  bends, crossings, and overlapping lines.

## Progress Tracking

When implementing a change, update progress docs so the repository shows the
actual state:

- Add completed work to `WHAT_WE_HAVE_DONE.md`.
- Add remaining validation or unfinished tasks to `IN_PROGRESS.md`.
- Remove or rewrite stale `IN_PROGRESS.md` items only when the work is truly
  done or no longer applies.
- Update `END_GOAL.md` if the implementation changes the target state or
  success criteria.

Keep progress notes factual. Prefer concrete statements over broad claims.

Good:

```text
- Added the SharePoint MCP server boundary with dry-run Graph client behavior.
- Validate one real Microsoft Graph file upload against the selected test site.
```

Avoid:

```text
- Finished all SharePoint integration.
- Make everything production ready.
```

## Code Style

Write code that is simple, explicit, and easy to test.

Prefer small functions and clear module boundaries. Add abstractions only when
they remove real duplication or clarify a real ownership boundary.

Keep downstream system code separated by server boundary:

- SharePoint behavior belongs under the SharePoint MCP server.
- CRM behavior belongs under the CRM MCP server.
- internal software behavior belongs under the internal software MCP server.
- shared cross-cutting helpers can live under `common/` when more than one
  server uses them.

Do not mix business workflow logic directly into cloud SDK clients.

## Code Comments

Comments should sound like a human maintainer explaining useful context.

Use comments when they explain why a choice exists, point out a sharp edge, or
make a non-obvious constraint clear. Do not narrate what the next line of code
already says.

Good:

```python
# Gateway passes only trusted caller claims through this path.
```

Avoid:

```python
# This function gets the user data and then returns the user data.
```

Do not add machine-like boilerplate comments, decorative section banners, or
obvious comments just to make code look documented.

## Security and Identity

Never log secrets, tokens, raw credentials, full sensitive records, or full
SharePoint document contents.

Treat CRM text fields, SharePoint documents, and MCP tool input as untrusted.
Validate all tool inputs before calling downstream systems.

For MCP identity:

- Gateway validates Entra-issued caller tokens.
- Runtime should not trust caller identity passed as ordinary tool arguments.
- Downstream SharePoint access uses separate downstream credentials.
- Do not reuse inbound MCP caller JWTs as Microsoft Graph tokens.

The SharePoint upload tool accepts only the inputs needed to upload one file.
Reject invalid `site_id`, `file_path`, or `content` with an error. Do not trim,
normalize, repair, or silently replace invalid input. SharePoint ACLs for
delegated access and `Sites.Selected` for application access remain the
downstream site-authorization boundary.

## Testing and Verification

When code changes, run the narrowest useful verification first, then broader
checks when the change touches shared behavior.

For documentation-only changes, verify links, filenames, ADR numbering, and
that README, ADRs, end goal, and progress files agree with each other.

If tests or validation cannot be run, state the reason clearly in the final
response.
