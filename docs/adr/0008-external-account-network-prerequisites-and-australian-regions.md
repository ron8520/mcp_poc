# ADR 0008: External Account and Network Prerequisites with Australian Regions

Date: 2026-07-29

Status: Accepted

## Context

The AgentCore workload Terraform root previously discovered its current AWS
account and region through `aws_caller_identity` and `aws_region` data sources,
and included a `gateway_private_access.tf` example that created the Gateway
interface endpoint.

The enterprise deployment model already has a central platform/TFE layer and a
separate network/platform account. That layer selects the workload account,
region, existing Runtime subnets and security groups. The network/platform
account owns AgentCore Gateway PrivateLink, private DNS, endpoint policy,
routing, and client-side network controls.

The primary deployment region is Sydney. AWS currently publishes AgentCore
Gateway/Runtime endpoints and VPC support for Sydney, but not Melbourne.
Melbourne therefore cannot yet be treated as an equivalent deployment region
for this stack.

## Decision

- Default `region` to Sydney (`ap-southeast-2`).
- Fail closed to Sydney for the current AgentCore Gateway/Runtime stack.
- Treat Melbourne (`ap-southeast-4`) as a future candidate. Enable it only
  after AWS publishes the required AgentCore endpoints and VPC support and the
  platform team validates a non-production deployment.
- Require `target_account_id` as an input supplied by central platform/TFE
  configuration.
- Build IAM and CloudWatch ARNs from `target_account_id` and `region`.
- Do not use `aws_caller_identity` or `aws_region` data sources in this
  workload root.
- Do not create or own the Gateway interface endpoint, private DNS, endpoint
  policy, corporate routing, or client-side security groups in this root.
- Continue to accept existing Runtime subnet and security-group IDs as workload
  inputs.

The central platform/TFE execution role remains responsible for authenticating
to the selected workload account. Its configured account must match
`target_account_id`.

## Consequences

Positive:

- The workload root matches the existing enterprise account and network
  ownership model.
- Plans no longer depend on account/region discovery APIs.
- Unsupported regional selections fail during Terraform input validation
  instead of later during service deployment.
- Private connectivity can be governed centrally without duplicating endpoint
  resources in each MCP workload state.

Tradeoffs:

- Terraform cannot independently prove that its execution credentials belong
  to `target_account_id` without reintroducing an account lookup.
- Central TFE configuration must prevent account-ID, region, subnet, and
  security-group drift.
- PrivateLink validation and rollback require coordination with the external
  network/platform owner.
- Enabling Melbourne requires a future reviewed change after AWS service
  availability and non-production validation.
- A successful workload plan does not prove that private DNS or corporate
  routing is functional.

## Operational Requirements

- Validate `target_account_id` against the selected TFE workspace and execution
  role before apply.
- Keep ECR, Secrets Manager, Runtime, logging, and AgentCore resources in the
  configured region unless a reviewed cross-region dependency is intentional.
- Test the external PrivateLink and private-DNS path in every environment.
- Record the network/platform owner and escalation path in the production
  runbook.
- Recheck the AWS AgentCore supported-regions, service-endpoints, and VPC
  support pages before adding another allowed region.

## Evidence

- [AgentCore supported regions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-regions.html)
- [AgentCore service endpoints](https://docs.aws.amazon.com/general/latest/gr/bedrock_agentcore.html)
- [AgentCore VPC supported Availability Zones](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html)

## Relationship to Earlier Decisions

This ADR clarifies the deployment ownership described in ADR 0001. It does not
change the shared Gateway, per-identity-lane Runtime, Entra, OBO, or direct
Cedar decisions in ADRs 0004, 0006, and 0007.
