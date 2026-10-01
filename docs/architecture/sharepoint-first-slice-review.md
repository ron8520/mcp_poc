# SharePoint MCP: engineering findings and validation backlog

For nontechnical reviewers, start with the [high-level architecture review](enterprise-mcp-platform-internal-review.md). This engineering follow-up records the open implementation problems, accountable owners and evidence required before each capability is enabled.

Initial review: 24 September 2026. Documentation updated: 1 October 2026.
Status: **open findings and proposed release gates; not deployment approval**.

This review is based on repository evidence, including the current working tree, Gateway interceptor/Cedar, Terraform references and ClickOps procedure. No AWS, Entra, Graph, SharePoint or deployed AgentCore environment was inspected or changed. A code, diagram or local test result does not close a live validation gate.

Phase one now includes a separate Dynamics 365/Dataverse CRM service under [ADR 0015](../adr/0015-dynamics-case-summary-app-only.md). This backlog remains SharePoint-specific; CRM acceptance is tracked by that ADR and the high-level review.

## Scope and current status

- **Implemented reference:** list metadata, bounded PDF text extraction and UTF-8 text upload; delegated MSAL OBO; fixed client-credentials code; an opt-in app-only caller-validation/resolver path; and separate Runtime lanes using the same service image.
- **Current delivery:** [EC2/CodeCommit/ECR/Console ClickOps](../clickops.md). Terraform is a long-term reference, not proof of the Console configuration. The nonprod reference has `LOG_ONLY` and app-only ingress disabled.
- **Target only:** native AgentCore Identity delegated OBO, validated per-app M2M operation, production CI/CD and wider integrations. App-only remains gated until its own acceptance tests pass.
- **Contract boundary:** ADR 0010's three-input upload contract and create-or-replace semantics remain unchanged. A public input, concurrency, identity-lane or deployment change requires a new ADR.

Existing implementation controls remain useful: invalid inputs and auth modes fail closed without identity fallback; inbound caller JWTs are separate from downstream credentials; Graph IDs and paths are encoded; file metadata is cross-checked; listing and PDF results are bounded; and exact lane-qualified Cedar actions and opt-in caller/site/tool mappings are present locally. These are repository facts, not proof of deployed permission enforcement.

## Open findings

Priority **P1** means close or explicitly constrain before the affected real-data pilot capability. **P2** means close before broad or production use. An accepted business tradeoff still needs dated evidence for the remaining operational controls.

| Finding | Problem and current evidence | Owner | Status and required evidence |
| --- | --- | --- | --- |
| **SP-01 P1 — Gateway bypass and service-role reuse** | `runtime_only_from_gateway` has only an `Allow` for `InvokeAgentRuntime`; the broad `agentcore_assume_role` trust is reused by Gateway and Runtime roles. Direct invocation, another AgentCore resource or the fixed application credential could bypass the intended boundary. | Platform / Security | **Open.** Add and validate explicit denial for non-Gateway principals, exact Gateway trust, Runtime and endpoint permissions, and administrative access. Test Gateway success, same-account direct denial, cross-account denial and another Gateway/Runtime cannot use the trusted role. |
| **SP-02 P1 — Policy may observe instead of block** | Nonprod uses `LOG_ONLY`; Cedar checks caller roles/scopes and lane-qualified tools but does not bind each caller to a site. Manual Console changes can bypass Terraform preconditions, and `Sites.Selected` is only the downstream application's maximum grant. | Security / Identity / Platform | **Open.** Measure only with controlled data, require `ENFORCE` for real-data role isolation, and test missing/extra roles, read versus upload, exact action names, tenant/client/audience/environment and delegated versus app-only denials. Keep app-only disabled until caller, resolver, provider and site tests pass. |
| **SP-03 P1 — Assertion provenance, token lifetime and OBO** | The interceptor copies bearer headers and does not validate JWTs itself; Runtime OBO uses the assertion. Header merging, token size, audience, Conditional Access, key rollover, expiry and revocation timing remain unverified. Caller token acquisition is unvalidated; the nonprod reference disables device-code flow. | Identity / Platform / Client | **Open.** Test actual Gateway SDK/header ordering, duplicate and opposite-lane header removal, concurrent users, v2 `aud` and MSAL client identity, consent, rollover, expiry, reauthentication and immediate deny/disable. Never log assertions or fall back to application identity. |
| **SP-04 P1 for writes — Upload response and audit boundary** | `upload_file` forwards the raw Graph JSON response and does not emit a complete service audit event; read/list and app-only audit paths have incomplete correlation/field controls. | Service / Security / Operations | **Open.** Project a minimal result, exclude URLs/credentials/unneeded personal data, use a trusted request identifier, capture safe outcome/latency/request ID/version, and test MCP, Gateway, Lambda, Runtime and client telemetry with seeded sensitive markers. |
| **SP-05 P1 for writes — Overwrite and ambiguous completion** | Path-based PUT keeps ADR 0010's create-or-replace contract without conditional versioning or automatic retry. Concurrent writes, timeout-after-commit, empty content and SharePoint library policies can leave uncertain outcomes. | SharePoint owner / Client owner | **Accepted contract; validation open.** Use a controlled path, accept the replacement behavior explicitly, test concurrency, timeout, empty/locked/read-only cases and version restore, and inspect uncertain completion before retry. Application rollback cannot restore business content. |
| **SP-06 P1 for PDF reads — Download capability and redirects** | Graph supplies a temporary preauthenticated download URL. The implementation checks the initial URL and byte count but does not yet enforce approved destinations across redirects. | Network / Service | **Partial controls; open.** Approve tenant download hosts, enforce HTTPS and destination policy on every redirect, deny inappropriate private/link-local destinations, never send the Graph bearer to download hosts, and test expiry and metadata/download permission races. |
| **SP-07 P1 bounded pilot / P2 scale — Resource exhaustion and incomplete results** | PDF extraction can do expensive work before truncation. Listing has item limits but no whole-tool call/deadline budget, cursor-loop detection, continuation output or explicit incomplete indicator. Upload and Graph JSON byte limits are not explicit. | Service / Operations | **Partial controls; open.** Set per-tool byte, wall-time and concurrency budgets, measure heavy PDFs, support cancellation, report empty/partial extraction, define unsupported formats, make listing completeness explicit and validate non-default libraries, moves and metadata shapes. |
| **SP-08 P1 — Returned content and data boundary** | PDF text is returned to the client; the MCP server does not control subsequent model, transcript or telemetry destinations. Document instructions could induce an agent to disclose or write other data. | Data owner / Client owner / Security | **Open.** Approve site classification, model/client destinations and retention; treat output as untrusted; test malicious documents with read-only and write-enabled principals; keep write authorization deterministic. |
| **SP-09 P1 runbook — Rotation and emergency disable** | The MSAL client reads Secrets Manager once and is cached for process lifetime. Replacing `AWSCURRENT` does not recycle existing processes; the opt-in provider lifecycle is separate. | Identity / Operations | **Open.** Define owner, expiry alert, overlap and recycle procedure; prove new processes use the new secret, revoke the old credential, test cache expiry and dependency loss, and disable new operations while old tokens remain valid. |
| **SP-10 P1 pilot / P2 tuning — Throttling, retries and deadlines** | Graph errors lose `Retry-After` and request IDs; no bounded read retry or composed end-to-end deadline is implemented. Upload failures propagate and must not be retried automatically. | Service / Client owner | **Open.** Choose one safe read-retry owner, preserve throttle metadata, honor `Retry-After` within the budget, propagate auth/config/permission failures without fallback, never retry writes, and test 429/503/DNS/TLS/cancellation amplification and pilot limits. |
| **SP-11 P1 — Release identity and rollback bundle** | ClickOps records deployment metadata, but code, Cedar, interceptor, Runtime configuration/header allowlists and Graph grants are independently mutable; the reference target invokes `DEFAULT`. A push does not deploy or synchronize tools. | Platform / Release | **Open.** Retain a manifest with commit, immutable image digest, Runtime/Gateway IDs, exact schema, policy/interceptor/config versions, identity/grant snapshots and tests. Synchronize and test a cohort, then exercise compatible code/config/policy/schema rollback without restoring revoked access. |
| **SP-12 P2 — Reproducibility and fresh-clone validation** | The image uses a floating Python base; key dependencies are unpinned. Optional pipeline references retain removed paths, mutable tags and shape-only checks; regression tests are local-only and not proven from a fresh clone. | Service / DevOps | **Open.** Record resolved dependencies/base digest, SBOM/provenance and compatibility, fix pipeline paths and immutable promotion before adoption, and provide a fresh-clone client → Gateway → Runtime smoke/negative procedure. Local compilation or image builds are not authorization coverage. |
| **SP-13 P1 pilot — Health, network reachability and recovery** | The Docker health check tests only local TCP reachability. Credentials are lazy, while PrivateLink/DNS/egress and logging/retention are externally owned. | Operations / Network / Platform | **Open.** Add an approved low-rate Graph read beside liveness, test cold start/restart, DNS/proxy/certificate, Secrets/KMS/ECR and download-host reachability, verify private and public route behavior, and agree dashboard thresholds, support, retention, SLO, outage and recovery procedures. |
| **SP-14 P1 assignment / P2 recurring — Configuration drift and lifecycle** | ClickOps, long-term Terraform and historical Azure DevOps references coexist. Per-app mappings and site grants can change independently, and ownership/cadence are not assigned. | Platform / Identity / SharePoint owners | **Open.** Assign approval and change owners, compare redacted Console configuration with the release manifest, review mappings/IAM provider union, remove retired grants and processes, test denial, and reconcile resources before Terraform adoption. |

Useful product references already supporting these findings include the [Microsoft OBO flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow), [Graph download behavior](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0), [Graph upload semantics](https://learn.microsoft.com/en-us/graph/api/driveitem-put-content?view=graph-rest-1.0), and [Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling).

## Minimum acceptance pack

A gate passes only with dated evidence from the selected AWS account/region and Microsoft tenant. This review and local tests close none of these gates.

| Gate | Required outcome | Accountable team | Current evidence |
| --- | --- | --- | --- |
| **G1 — Controlled delegated read** | SP-01 boundary closed; SP-02 enforcement; SP-03 OBO and header negatives; approved data/client scope; bounded PDF/list behavior and network paths | Platform + Identity + Security + data owner | Code reviewed; live evidence absent |
| **G2 — Pilot operations** | Request/failure audit, safe logs, rate/deadline limits, synthetic health, on-call/kill-switch, secret rotation and compatible rollback demonstrated | Operations + service owner | Partial code/procedure; drills absent |
| **G3 — Optional upload** | G1/G2 plus SP-04 result/audit, SP-05 overwrite acceptance and restore, denied upload role, empty-content and ambiguous-completion tests | SharePoint + Security + client owner | Contract accepted in ADR 0010; closure evidence absent |
| **G4 — Optional app-only** | G1/G2 plus signed v2 app context, exact caller/site/tool mapping, selected-site/provider IAM denies, no delegated token accepted, cross-app and cross-environment tests | Identity + Platform + Security | Opt-in reference implemented; ingress disabled |
| **G5 — Broader or production use** | Immutable reproducible release evidence, sustainable regression procedure, measured capacity/SLO, patch/offboarding/drift owners and recurring reviews | Service owner + Operations | Open |

The intended progression is controlled delegated reads → reliable operations →
upload if required → app-only only when an autonomous use case needs it. A
read-only start does not change the three-tool contract or remove the need for
enforced roles and policy.

For every test record the finding/gate ID, date, environment/tenant/account/
region, deployed manifest, expected and actual outcome, redacted trace/request
IDs, executor, reviewer and follow-up. At minimum test two users with different
ACLs; read-only versus upload role; wrong site/drive/item; wrong
tenant/client/audience/lane; forged assertion; non-Gateway invocation;
timeout-after-write; throttling; rotation; and rollback. Do not store live
tokens or document contents as evidence.

## Decisions still needed for pilot

1. Pilot lane, users, approved site/library and data classification, including
   client/model processing destinations.
2. Whether create-or-replace upload is needed now and who accepts its
   collision/restore semantics under ADR 0010.
3. Named owners and evidence for G1–G3; app-only stays out unless G4 is in
   scope.
4. Payload, deadline and concurrency limits, SLO/support hours, recovery and
   kill-switch time.
5. Patch, permission-review, drift-detection and credential-rotation cadence,
   plus a fresh-clone procedure another operator can reproduce.

The high-level internal architecture review records business/data-owner
decisions and target context. This engineering review owns the implementation
findings and release gates. Any qualitative risk discussion in the business
review is context for that decision; it is not measured risk reduction and does
not close a gate. Only dated evidence from the selected AWS account and
Microsoft tenant can change the open statuses above.
