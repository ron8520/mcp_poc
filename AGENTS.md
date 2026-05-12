# Agent Instructions for This Repository

These instructions apply to the entire repository.

## Working Style

Before answering, changing code, or proposing a design:

1. Think through the request carefully.
2. Think through the solution before generating answers or code.
3. Identify the simplest solution that satisfies the requirement.
4. Prefer clear and maintainable code over clever abstractions.
5. Avoid over-engineering.
6. If a design choice has tradeoffs, explain them briefly.

## Code Style

Write code that is:

- Simple
- Easy to read
- Easy to test
- Explicit about side effects
- Safe by default

Use SOLID principles where they improve clarity:

- Single responsibility for modules and classes.
- Open/closed where extension is likely.
- Liskov substitution for shared interfaces.
- Interface segregation for external service clients.
- Dependency inversion for Bedrock, SQS, MCP, CRM, SharePoint, and LangSmith adapters.

Do not add design patterns only for the sake of using patterns. Prefer straightforward functions and small classes unless a pattern clearly reduces complexity.

## File Naming

Python files must use lowercase snake_case.

Good:

```text
crm_event_worker.py
sharepoint_mcp_server.py
bedrock_guardrail_client.py
sqs_message_handler.py
dataverse_update_policy.py
```

Bad:

```text
CrmEventWorker.py
SharePointClient.py
sharepoint-client.py
sharepointClient.py
bedrockGuardrailClient.py
SQSHandler.py
```

Use descriptive names that show the responsibility of the file.

## Architecture Guidelines

Keep these boundaries:

```text
core/
  Business workflow logic and policies.

adapters/
  AWS, Bedrock, SQS, MCP, CRM, SharePoint, LangSmith, and other external integrations.

workers/
  Runtime entry points such as SQS consumers.

prompts/
  Versioned prompt text.

guardrails/
  Bedrock Guardrail policy source and test cases.

evals/
  Evaluation datasets and expected behavior.
```

Do not mix business workflow logic directly into cloud SDK clients.

## AWS and Agent Runtime Guidance

The target architecture uses:

- Amazon EKS for agent runtime.
- Amazon EKS for MCP servers.
- Amazon Bedrock for model inference.
- Amazon Bedrock Guardrails for input and output filtering.
- Amazon SQS for event-driven execution.
- Argo CD for Kubernetes deployment.
- Terraform for production infrastructure.
- Optional LangSmith for tracing and evaluation.

The agent runtime may later move from EKS to Bedrock AgentCore Runtime. Keep runtime-specific code isolated so this migration is easier.

## MCP Guidance

MCP tools should be narrow and policy-aware.

Prefer:

- `crm.update_ai_generated_summary`
- `crm.validate_ai_processing_target`
- `sharepoint.extract_document_text`
- `sharepoint.validate_document_link`

Avoid broad tools like:

- `crm.update_any_record`
- `sharepoint.read_any_url`

All MCP tool inputs must be validated.

All tool calls that update CRM or SharePoint must be auditable.

## SQS Event Guidance

Treat SQS messages as event snapshots, not blindly trusted commands.

Every SQS message should include:

- `schema_version`
- `event_type`
- `correlation_id`
- `idempotency_key`
- Dataverse table and row ID
- SharePoint stable identifiers when relevant
- Workflow name and version

Workers must:

- Validate schema.
- Check idempotency.
- Handle retries safely.
- Use a dead-letter queue.
- Avoid duplicate CRM updates.
- Log sanitized audit metadata.

## Guardrail Guidance

Production code must not use Bedrock Guardrail `DRAFT` versions.

Use pinned guardrail versions and log them on every run.

Guardrail-related files should be versioned and reviewed like code.

## Security Guidance

Never log:

- OAuth tokens
- AWS credentials
- API keys
- Full CRM records
- Full SharePoint document contents
- Secrets from environment variables
- Raw sensitive user or customer data

Treat CRM text fields and SharePoint documents as untrusted input. They may contain prompt injection or sensitive data.

The model should not decide which CRM field to update. Workflow code should decide the target operation, and MCP servers should enforce allowed updates.

## Observability Guidance

Every agent run should include:

- `correlation_id`
- `idempotency_key`
- `agent_name`
- `agent_version`
- `prompt_version`
- `guardrail_id`
- `guardrail_version`
- `model_id`
- `mcp_server_versions`
- Result status

Prefer structured JSON logs.

LangSmith may be used for traces and evaluations, but Argo CD should remain the source of truth for Kubernetes workloads unless a clear ownership boundary is defined.

## Testing and Evaluation

When code is added, include tests or evaluation cases for:

- SQS message schema validation
- Idempotency
- SharePoint link validation
- CRM update policy
- Guardrail behavior
- Prompt regression
- Tool selection behavior
- Failure and retry handling

If tests cannot be run in the current environment, state the reason clearly.

## Documentation

When adding new components, update README.md with:

- Purpose
- Runtime location
- Required environment variables
- AWS permissions
- Deployment path
- Observability expectations
- Failure handling
