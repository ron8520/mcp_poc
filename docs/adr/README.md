# Architecture Decision Records

This directory preserves the numbered architecture decision history. Read the
following ADRs first for the current PoC and target shape:

1. [ADR 0004: Entra JWT and server-side AWS IAM](0004-claude-code-entra-jwt-mcp-boundary.md)
2. [ADR 0006: Direct Cedar and SharePoint identity lanes](0006-direct-cedar-and-dual-sharepoint-identity-lanes.md)
3. [ADR 0008: External account, network, and Australian regions](0008-external-account-network-prerequisites-and-australian-regions.md)
4. [ADR 0010: SharePoint upload contract and lane names](0010-simple-sharepoint-upload-and-credential-lane-names.md)
5. [ADR 0012: AgentCore Identity delegated and M2M lanes](0012-agentcore-identity-for-delegated-and-m2m-lanes.md)
6. [ADR 0013: Staged app-only catalog and BAU rollout](0013-staged-entra-app-only-catalog-and-bau-rollout.md)
7. [ADR 0015: Dynamics 365 case-summary MCP operation](0015-dynamics-case-summary-app-only.md)

The remaining ADRs are retained for traceability:

- [ADR 0001](0001-agentcore-runtime-mcp-platform.md) is the historical platform
  baseline. Later ADRs qualify its authorization, target, and deployment details.
- [ADR 0002](0002-policy-as-code-and-devops-workflows.md) and
  [ADR 0011](0011-trust-domain-runtime-and-app-only-identity-resolver.md) are
  superseded records.
- [ADR 0003](0003-azure-devops-cloud-owned-platform-repo.md),
  [ADR 0005](0005-path-scoped-policy-pr-validation.md), and
  [ADR 0009](0009-vendor-native-and-documentation-mcp-targets.md) are future or
  conditional operating and target references.
- [ADR 0007](0007-identity-lanes-by-downstream-credential-mode.md) and
  [ADR 0014](0014-phase-one-crm-case-field-app-only.md) retain overlapping
  predecessor decisions. ADR 0015 makes the CRM operation concrete.

Read ADR 0006 with ADRs 0010 and 0012 for the later tool/lane names and target
OAuth decision. The current deployment procedure is [ClickOps](../clickops.md);
the Terraform and Azure DevOps delivery proposals remain future references.

The status of an ADR records the decision state; it does not by itself prove a
deployed or live-validated integration. Current implementation, target design,
and remaining validation gates are stated in the individual ADRs and the main
repository documentation.
