# MCP PoC on AWS

This repository is for building a proof of concept for an enterprise-grade MCP-based agent solution on AWS.

The target solution connects:

- Microsoft SharePoint
- Microsoft Dynamics 365 / Dataverse / CRM
- MCP servers
- Agent runtime on Amazon EKS
- Amazon Bedrock for model inference
- Amazon Bedrock Guardrails for input and output safety
- Amazon SQS for event-driven agent triggers
- Argo CD for GitOps deployment
- Optional LangSmith for tracing, evaluation, and agent observability

## Target Architecture

High-level flow:

```text
Dataverse attribute update
  ↓
Power Automate
  ↓
Amazon SQS
  ↓
Agent worker on EKS
  ↓
Amazon Bedrock + Bedrock Guardrails
  ↓
MCP servers on EKS
  ↓
SharePoint and CRM APIs
```

The main runtime components are:

| Component | Purpose |
| --- | --- |
| Agent EKS cluster | Runs agent API services and SQS workers. |
| MCP EKS cluster | Runs SharePoint and CRM MCP servers. |
| Amazon Bedrock | Provides model inference. |
| Bedrock Guardrails | Filters user input, event context, retrieved content, and model output. |
| Amazon SQS | Decouples Power Automate events from agent processing. |
| Argo CD | Manages Kubernetes deployment state. |
| CodeCommit | Current source control system. |
| LangSmith | Optional tracing, evaluation, and observability platform. |

## Event-Driven Flow

The preferred event flow for the current PoC is:

1. A specific Dataverse attribute changes.
2. Power Automate detects the change.
3. Power Automate sends a structured message to SQS.
4. The EKS agent worker consumes the message.
5. The worker validates message schema and idempotency.
6. The agent uses SharePoint MCP to access the target SharePoint item.
7. The agent uses Bedrock and Guardrails to generate output.
8. The CRM MCP performs a controlled Dataverse update.
9. The worker records audit metadata and deletes the SQS message.

SQS messages should contain stable identifiers, not full sensitive business records.

Recommended message fields:

```json
{
  "schema_version": "1.0",
  "event_type": "dataverse.sharepoint_document_ready",
  "correlation_id": "uuid",
  "idempotency_key": "environment:table:row_id:row_version",
  "dataverse": {
    "environment": "nonprod",
    "table": "account",
    "row_id": "00000000-0000-0000-0000-000000000000",
    "row_version": "123456",
    "etag": "W/\"123456\"",
    "modified_on": "2026-05-12T10:12:30Z"
  },
  "sharepoint": {
    "site_id": "site-id",
    "drive_id": "drive-id",
    "item_id": "item-id",
    "url": "https://contoso.sharepoint.com/sites/example/document.docx"
  },
  "workflow": {
    "name": "generate_document_summary",
    "version": "1.0",
    "target_crm_field": "new_ai_generated_summary",
    "requires_human_approval": false
  }
}
```

## Power Automate and SQS

For this PoC, direct Power Automate to SQS is acceptable because the trigger is a controlled system-to-system Dataverse event, not an arbitrary user-submitted request.

Production controls should include:

- Dedicated AWS principal for the Power Automate SQS connector.
- IAM permission limited to `sqs:SendMessage` on the target queue.
- Separate queues for nonproduction and production.
- SQS dead-letter queue.
- CloudWatch alarms.
- Message schema validation in the worker.
- Idempotency protection.
- Audit logging.
- Conditional or validated CRM updates.

If the flow later becomes user-facing or accepts arbitrary requests, add an ingestion layer:

```text
Power Automate
  ↓
API Gateway + AWS WAF
  ↓
Lambda validation
  ↓
SQS
```

## MCP Servers

Planned MCP servers:

```text
mcp_servers/
  sharepoint/
  crm/
```

Recommended SharePoint MCP tools:

- `sharepoint.validate_document_link`
- `sharepoint.get_document_metadata`
- `sharepoint.extract_document_text`

Recommended CRM MCP tools:

- `crm.validate_ai_processing_target`
- `crm.mark_ai_processing_started`
- `crm.update_ai_generated_summary`
- `crm.mark_ai_processing_completed`
- `crm.mark_ai_processing_failed`

Avoid exposing broad generic tools like:

- `crm.update_record`
- `sharepoint.read_any_url`

Prefer narrow, workflow-specific tools with strong validation.

## Guardrail Management

Guardrails should be versioned and promoted like application code.

Recommended files:

```text
guardrails/
  crm_sharepoint/
    policy.yaml
    denied_topics.json
    pii_policy.json
    test_cases.jsonl
    release_notes.md
```

Production should use immutable Bedrock Guardrail versions, not `DRAFT`.

The agent runtime should log:

- Guardrail ID
- Guardrail version
- Logical guardrail release
- Agent version
- Prompt version
- Model ID
- MCP server versions

## Terraform and Argo CD

Recommended ownership boundary:

| Tool | Owns |
| --- | --- |
| Terraform | AWS infrastructure, EKS, SQS, IAM, Bedrock Guardrails, ECR, VPC, SSM parameters |
| Argo CD | Kubernetes workloads, Helm values, namespaces, services, deployments |
| Application code | Agent source, MCP source, prompt source, eval datasets |
| LangSmith | Optional tracing, evaluation, and observability |

Production should pin exact image tags or digests. Do not use `latest`.

## LangSmith

LangSmith can be used for:

- Agent traces
- Prompt debugging
- Evaluation datasets
- Regression testing
- Human review of runs

Initial recommendation:

- Argo CD owns agent deployment.
- LangSmith observes agent behavior.

Avoid allowing both Argo CD and LangSmith to manage the same Kubernetes Deployment objects unless ownership boundaries are clearly separated.

## Repository Layout

Target layout:

```text
agents/
  crm_sharepoint_agent/
    src/
    prompts/
    evals/
    config/
    helm/

mcp_servers/
  sharepoint/
    src/
    helm/
  crm/
    src/
    helm/

guardrails/
  crm_sharepoint/
    policy.yaml
    test_cases.jsonl

terraform/
  modules/
  envs/

deploy/
  nonprod/
  production/

scripts/
```

## Python Naming Convention

Python file names must use lowercase snake_case.

Good examples:

```text
crm_event_worker.py
sharepoint_mcp_server.py
bedrock_guardrail_client.py
sqs_message_handler.py
dataverse_update_policy.py
```

Bad examples:

```text
CrmEventWorker.py
SharePointClient.py
sharepoint-client.py
sharepointClient.py
bedrockGuardrailClient.py
SQSHandler.py
```
