# People Assist Backend

People Assist is an internal HR policy assistant running on AWS Lambda.

The backend receives a question from the Chainlit frontend, checks the question against Amazon Bedrock Guardrails, determines what the user is asking, retrieves HR policy content when required, and generates a response using Amazon Bedrock.

The backend currently uses:

- AWS Lambda with Python 3.12
- LangGraph for workflow orchestration
- Amazon Bedrock Guardrails
- Amazon Bedrock Converse API
- Anthropic Claude Sonnet 4.5 through the Australian inference profile
- Amazon Kendra for HR policy retrieval
- A ZIP-based Lambda function package
- A separate ZIP-based Lambda dependency layer

The main purpose of the new workflow is to make request handling more predictable.

Questions such as `Who are you?` should not search Kendra. Unrelated questions should not return references to random HR documents. When a guardrail blocks a request or response, citations should not be returned.

---

## Current implementation

The backend currently supports:

- Chainlit-to-Lambda requests
- Input validation
- Independent Bedrock Guardrail input scanning
- Model-based intent detection
- Direct responses to questions about People Assist
- Out-of-scope handling
- Kendra retrieval for HR policy questions
- Final answer generation through Bedrock Converse
- Final response guardrail enforcement
- Kendra citation formatting
- Lambda deployment using ZIP packages and a Lambda layer

The backend currently does not support:

- API Gateway request bodies
- Dictionary request bodies
- Conversation history
- LangGraph checkpoint persistence
- User identity or employee profile lookup
- Personal leave balance lookup
- Email sending
- ServiceNow integration
- Tool calling
- Human approval workflows
- Automated intent-router evaluation

Router and RAG evaluation will be added after the main workflow is stable.

---

## Request flow

The backend follows this order:

```text
Chainlit question
    |
    v
Validate request
    |
    v
Apply input guardrail
    |
    v
Detect intent
    |
    +---------------------+---------------------+
    |                     |                     |
    v                     v                     v
HR policy             Direct answer         Out of scope
    |                     |                     |
    v                     v                     v
Kendra retrieval       Fixed response        Fixed response
    |                  No citations          No citations
    v
Generate HR answer
    |
    v
Final Bedrock guardrail
    |
    v
Format response
    |
    v
Return message and citations
```

The ordering is important.

The input guardrail runs before the intent model. The intent model runs before Kendra. Kendra only runs when the selected intent is `hr_policy`.

---

## Input guardrail

The input guardrail checks whether the question is safe and allowed to continue through the application.

It can enforce configured controls such as:

- Harmful content
- Denied topics
- Prompt attacks
- Sensitive information rules
- Organisation-specific safety policies

The input guardrail is not used to decide whether a question is related to HR.

For example:

```text
Who are you?
```

is normally safe. The guardrail should allow it, and the intent router should classify it as `direct_answer`.

When the input guardrail intervenes:

- Intent detection is skipped
- Kendra is skipped
- Final answer generation is skipped
- Citations are empty

---

## Intent detection

After the input passes the guardrail, the backend uses a Bedrock model to classify the question.

The router currently uses:

```text
au.anthropic.claude-sonnet-4-5-20250929-v1:0
```

This is the Australian geographic inference profile for Anthropic Claude Sonnet 4.5.

The router returns one of three values:

```text
hr_policy
direct_answer
out_of_scope
```

The router does not answer the user. It only selects the next application path.

### `hr_policy`

Used when the user is asking about an HR policy, entitlement, procedure, workplace process or employee support information.

Examples:

```text
How many sick leave days do I get?
Can I work from home?
My child is sick. Can I take leave?
Can my manager ask me for a medical certificate?
What support is available if I am being bullied?
How do I claim work travel expenses?
```

Processing:

```text
Input guardrail
→ Intent router
→ Kendra
→ Final answer model
→ Citations
```

### `direct_answer`

Used when the user is asking about People Assist itself.

Examples:

```text
Who are you?
What is People Assist?
What can you help me with?
Are you part of HR?
Where does your information come from?
```

Processing:

```text
Input guardrail
→ Intent router
→ Fixed People Assist response
→ No Kendra call
→ No final answer model call
→ No citations
```

### `out_of_scope`

Used when the request is unrelated to People Assist or HR policy information.

Examples:

```text
Who won the football match?
What is the weather tomorrow?
Write Python code for me.
Tell me a joke.
Give me betting advice.
```

Processing:

```text
Input guardrail
→ Intent router
→ Fixed out-of-scope response
→ No Kendra call
→ No final answer model call
→ No citations
```

---

## Retrieval

Amazon Kendra is currently used to retrieve HR policy content.

Retrieval only runs when:

```text
route == hr_policy
```

This prevents unrelated questions from returning irrelevant policy documents.

For example, this question must not reach Kendra:

```text
Who are you?
```

The router should return:

```text
direct_answer
```

and the graph should go directly to response formatting.

The retrieval implementation returns a common internal `RetrievedDocument` structure containing fields such as:

- Document content
- Document title
- Source URL
- Page number
- Relevance score
- Provider
- Original metadata

The graph does not directly depend on Kendra-specific response objects.

A Bedrock Knowledge Base retriever may be tested later, but Kendra is the current production retrieval provider.

---

## Final answer generation

For an HR policy request, the retrieved Kendra documents are passed to the final Bedrock model.

The final answer model currently uses the configured Claude Sonnet 4.5 Australian inference profile.

The final model is instructed to:

- Answer using only the retrieved HR policy content
- Avoid inventing policy rules
- Mention the relevant policy document
- State when the retrieved documents do not contain the answer
- Avoid inline reference markers such as `[1]`
- Use plain employee-friendly language
- Keep the response professional and clear
- Be empathetic for sensitive employee situations

The response prompt includes a style example. The example is used to guide response structure only and must not be treated as real policy content.

---

## Citation handling

Citations are returned only when all of these conditions are true:

- The selected route is `hr_policy`
- Kendra retrieval was called
- Kendra returned documents
- The input guardrail did not intervene
- The final model guardrail did not intervene
- Answer generation completed successfully

Citations must be empty when:

- The route is `direct_answer`
- The route is `out_of_scope`
- The input guardrail blocks the request
- The final answer guardrail intervenes
- Intent detection fails
- Retrieval fails
- Answer generation fails
- No relevant documents are returned

Example non-HR response:

```json
{
  "message": "I’m People Assist, an internal HR policy assistant.",
  "citations": []
}
```

This citation suppression is handled explicitly in the backend. It should not rely on the frontend or guardrail to remove references.

---

## Repository structure

```text
src/
├── citations/
│   ├── __init__.py
│   └── formatter.py
│
├── graph/
│   ├── __init__.py
│   ├── builder.py
│   ├── nodes.py
│   └── state.py
│
├── guardrails/
│   ├── __init__.py
│   └── input_scan.py
│
├── llm/
│   ├── __init__.py
│   └── bedrock.py
│
├── models/
│   ├── __init__.py
│   ├── citations.py
│   └── documents.py
│
├── prompts/
│   ├── __init__.py
│   └── people_assist.py
│
├── retrieval/
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   └── kendra.py
│
├── routing/
│   ├── __init__.py
│   └── semantic_router.py
│
├── config.py
└── people_assist_lambda.py

requirements.txt
README.md
```

There is no Dockerfile in the current deployment.

---

## Folder responsibilities

### `citations/`

Contains citation formatting logic.

`formatter.py` converts retrieved Kendra documents into the citation structure expected by Chainlit.

It is responsible for:

- Formatting URLs
- Adding page fragments where available
- Producing short excerpts
- Removing duplicate references

### `graph/`

Contains the LangGraph workflow.

- `state.py` defines graph input, output and shared state.
- `nodes.py` contains the functions executed at each workflow stage.
- `builder.py` connects the nodes and compiles the graph.

The graph controls whether a request continues to the guardrail, router, Kendra or response formatter.

### `guardrails/`

Contains the independent input guardrail integration.

`input_scan.py` calls Bedrock `ApplyGuardrail` before the intent model is invoked.

### `llm/`

Contains the final Bedrock answer-model integration.

`bedrock.py` calls the Bedrock Converse API and returns:

- Generated answer text
- Whether the final guardrail intervened

The final answer model and intent router are separate components even though they currently use the same Claude Sonnet 4.5 AU inference profile.

### `models/`

Contains shared data structures.

- `RetrievedDocument` represents normalised Kendra results.
- `Citation` defines the response citation shape.

### `prompts/`

Contains the final answer prompt and context formatting logic.

The intent-router prompt remains with the routing implementation because it is specific to intent classification.

### `retrieval/`

Contains Kendra retrieval logic.

- `base.py` defines the retriever interface.
- `kendra.py` maps Kendra results into `RetrievedDocument`.
- `factory.py` creates the configured retriever.

### `routing/`

Contains intent detection.

`semantic_router.py` calls the configured Bedrock model and classifies the question as:

```text
hr_policy
direct_answer
out_of_scope
```

### `config.py`

Loads configuration from Lambda environment variables.

### `people_assist_lambda.py`

Contains the Lambda entry point.

It:

- Reads the Chainlit question
- Invokes the LangGraph workflow
- Returns the generated message and citations
- Handles unexpected top-level failures

---

## Input contract

The Lambda currently supports only the Chainlit backend request format:

```json
{
  "text": "How many sick leave days do I get?"
}
```

The handler reads:

```python
question = str(event.get("text") or "").strip()
```

The following formats are not currently supported:

```json
{
  "body": "{\"text\":\"...\"}"
}
```

```json
{
  "body": {
    "text": "..."
  }
}
```

There is no API Gateway request parsing in the current Lambda handler.

---

## Output contract

The Lambda returns:

```json
{
  "message": "According to the relevant leave policy...",
  "citations": [
    {
      "title": "Leave Policy.pdf",
      "url": "https://example.sharepoint.com/Leave%20Policy.pdf#page=4",
      "excerpt": "Employees may access personal leave...",
      "provider": "kendra",
      "page_number": 4
    }
  ]
}
```

For direct or unrelated questions:

```json
{
  "message": "I’m designed to help with HR policy questions.",
  "citations": []
}
```

For blocked requests:

```json
{
  "message": "Sorry, I cannot help with that request.",
  "citations": []
}
```

---

## Runtime

The Lambda function uses:

```text
Python 3.12
```

The layer must also be built for Python 3.12.

Use the same Python version during the dependency build to reduce the risk of compatibility issues, especially if a dependency contains platform-specific binaries.

---

## Deployment approach

The current deployment uses two ZIP archives:

```text
function.zip
  Application source code

package.zip
  Third-party dependencies used as a Lambda layer
```

### Why container deployment is not used

Lambda container deployment was tested but is not used in the current solution because of the current ECR and Lambda permission setup.

The Dockerfile should therefore be removed from this backend.

### Why Docker is not used to build the layer

A Docker-based layer build was also tested.

The resulting dependency layer exceeded the supported Lambda deployment size, so this method is not used.

The dependency layer is now created directly as a ZIP file through the build pipeline.

The current ZIP-based layer is below 200 MB uncompressed and deploys successfully.

---

## Building the Lambda layer

The layer ZIP must have this structure:

```text
package.zip
└── python/
    ├── boto3/
    ├── langchain_aws/
    ├── langgraph/
    └── other dependencies
```

Example pipeline commands:

```yaml
build:
  commands:
    - python3.12 --version
    - pip config set global.target ""
    - rm -rf package package.zip
    - mkdir -p package/python

    - python3.12 -m pip install --target package/python -r requirements.txt

    - find package/python -type d -name "__pycache__" -prune -exec rm -rf {} +
    - find package/python -type d -name "tests" -prune -exec rm -rf {} +
    - find package/python -type d -name "test" -prune -exec rm -rf {} +

    - du -sh package/python

    - cd package
    - zip -r ../package.zip python
    - cd ..

    - du -sh package.zip

artifacts:
  files:
    - package.zip
```

Do not remove every `*.dist-info` directory. Some Python libraries use installed package metadata at runtime.

---

## Building the function ZIP

Zip the contents of `src/`, not the `src` directory itself.

```bash
rm -f function.zip

cd src
zip -r ../function.zip .
cd ..
```

Expected structure:

```text
function.zip
├── people_assist_lambda.py
├── config.py
├── citations/
├── graph/
├── guardrails/
├── llm/
├── models/
├── prompts/
├── retrieval/
└── routing/
```

Lambda handler:

```text
people_assist_lambda.handler
```

---

## Dependencies

The direct backend dependencies are:

```text
boto3
langchain-aws
langgraph
```

Their responsibilities are:

```text
boto3
  ApplyGuardrail
  Bedrock Converse for intent detection
  Bedrock Converse for final answer generation

langchain-aws
  Amazon Kendra retriever

langgraph
  Workflow state and conditional routing
```

The backend no longer needs to directly install:

```text
langchain-community
numpy
pydantic
```

Any required transitive dependency should be resolved through the packages listed in `requirements.txt`.

---

## Environment variables

### Required configuration

| Variable | Description |
|---|---|
| `MODEL_ID` | Bedrock model or inference profile used for the final HR answer |
| `ROUTER_MODEL_ID` | Bedrock model or inference profile used for intent detection |
| `KENDRA_INDEX_ID` | Kendra index used for policy retrieval |
| `GUARDRAIL_ID` | Published Bedrock Guardrail ID |
| `GUARDRAIL_VERSION` | Published Bedrock Guardrail version |

Recommended current model values:

```text
MODEL_ID=au.anthropic.claude-sonnet-4-5-20250929-v1:0
ROUTER_MODEL_ID=au.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### Model configuration

| Variable | Default | Description |
|---|---:|---|
| `MAX_TOKENS` | `4096` | Maximum output tokens for the final HR answer |
| `TEMPERATURE` | `0` | Final answer temperature |
| `ROUTER_MAX_TOKENS` | Depends on router response format | Maximum output tokens for intent detection |
| `ROUTER_TEMPERATURE` | `0` | Intent router temperature |

### Retrieval configuration

| Variable | Default | Description |
|---|---:|---|
| `RETRIEVAL_TOP_K` | `5` | Maximum number of Kendra results |
| `KENDRA_MIN_SCORE_CONFIDENCE` | `0` | Minimum Kendra confidence threshold |

### Guardrail configuration

| Variable | Default | Description |
|---|---:|---|
| `ENABLE_INPUT_GUARDRAIL_SCAN` | `true` | Enables the independent input scan |

`AWS_REGION` is provided by Lambda and should be set to `ap-southeast-2` for local testing.

---

## IAM permissions

The Lambda execution role needs permission to invoke the configured inference profile, apply the guardrail and search the Kendra index.

### Bedrock

```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": [
    "<Claude-Sonnet-4.5-AU-inference-profile-ARN>",
    "<destination-foundation-model-ARNs-required-by-the-profile>"
  ]
}
```

### Guardrail

```json
{
  "Effect": "Allow",
  "Action": "bedrock:ApplyGuardrail",
  "Resource": "<guardrail-arn>"
}
```

### Kendra

```json
{
  "Effect": "Allow",
  "Action": [
    "kendra:Retrieve"
  ],
  "Resource": "<kendra-index-arn>"
}
```

The exact Bedrock permissions depend on how the inference profile and destination model resources are restricted in the account and organisation policies.

---

## Lambda handler

The handler only supports the current Chainlit payload.

```python
def handler(
    event: dict[str, Any],
    context: Any,
) -> dict[str, Any]:
    try:
        question = str(
            event.get("text") or ""
        ).strip()

        result = GRAPH.invoke(
            {
                "question": question,
            }
        )

        return {
            "message": result.get(
                "message",
                "I could not generate a response.",
            ),
            "citations": result.get(
                "citations",
                [],
            ),
        }

    except Exception:
        logger.exception(
            "People Assist request failed"
        )

        return {
            "message": (
                "Sorry, something went wrong while "
                "processing your request."
            ),
            "citations": [],
        }
```

There is intentionally no API Gateway body parser.

---

## Local testing

Set:

```bash
export PYTHONPATH=src
export AWS_REGION=ap-southeast-2

export MODEL_ID=au.anthropic.claude-sonnet-4-5-20250929-v1:0
export ROUTER_MODEL_ID=au.anthropic.claude-sonnet-4-5-20250929-v1:0

export ENABLE_INPUT_GUARDRAIL_SCAN=true
export GUARDRAIL_ID=<guardrail-id>
export GUARDRAIL_VERSION=<guardrail-version>

export KENDRA_INDEX_ID=<kendra-index-id>
export RETRIEVAL_TOP_K=5
export KENDRA_MIN_SCORE_CONFIDENCE=0.5
```

Example invocation:

```bash
python - <<'PY'
from people_assist_lambda import handler

questions = [
    "Who are you?",
    "How many sick leave days do I get?",
    "Who won the football match?",
]

for question in questions:
    response = handler(
        {
            "text": question,
        },
        None,
    )

    print()
    print("Question:", question)
    print("Response:", response)
PY
```

Expected behaviour:

```text
Who are you?
→ direct_answer
→ no Kendra
→ no citations

How many sick leave days do I get?
→ hr_policy
→ Kendra
→ final answer model
→ citations

Who won the football match?
→ out_of_scope
→ no Kendra
→ no citations
```

---

## Logging

The backend writes logs to the Lambda CloudWatch log group.

Useful fields include:

```text
request_id
route
router_model_id
retrieval_result_count
citation_count
guardrail_intervened
error_type
latency
token usage
```

Avoid logging these values by default:

```text
full user question
retrieved document content
full model prompt
full model response
employee names
health information
personal HR details
```

---

## Error handling

Expected application failures should return a safe message with no citations.

### Invalid input

```json
{
  "message": "No valid text input was provided.",
  "citations": []
}
```

### Guardrail scan failure

```json
{
  "message": "Sorry, I could not safely process your request at this time.",
  "citations": []
}
```

### Intent routing failure

```json
{
  "message": "Sorry, I could not determine how to process your request. Please try rephrasing it.",
  "citations": []
}
```

### Answer generation failure

```json
{
  "message": "Sorry, I could not generate an answer at this time.",
  "citations": []
}
```

### Unexpected failure

```json
{
  "message": "Sorry, something went wrong while processing your request.",
  "citations": []
}
```

---

## Known limitations

### Additional router call

Every allowed request currently uses a Bedrock model call for intent classification.

Because the router currently uses Claude Sonnet 4.5, the intent call is not using a separate smaller model. Cost and latency will be evaluated later.

### No conversation history

Each question is processed independently.

A follow-up such as:

```text
How about contractors?
```

does not have enough context unless the frontend includes the previous topic.

### No user-specific employee data

The assistant cannot currently answer:

```text
How much leave do I personally have?
What is my salary?
Who is my manager?
```

It only uses HR policy documents retrieved from Kendra.

### No sentence-level citation attribution

Citations are based on the retrieved Kendra documents.

The backend does not yet prove which individual document supports each sentence in the final answer.

### No automated router evaluation

Intent-routing metrics and test datasets will be added later.

### Kendra is the only active retriever

Bedrock Knowledge Base may be evaluated later, but it is not part of the current active flow.

---

## Future work

Likely next steps are:

1. Test the three intent routes with a labelled dataset.
2. Add router accuracy and confusion-matrix reporting.
3. Add CloudWatch metrics for route, latency, token use and citation count.
4. Review Kendra relevance thresholds.
5. Add retrieval quality evaluation.
6. Add conversation history.
7. Add an HR email drafting flow with user confirmation.
8. Add more detailed citation attribution.
9. Add prompt and model version tracking.

ServiceNow is not part of the current implementation or planned workflow described by this repository.

---

## Development rules

When modifying the backend:

- Keep the runtime compatible with Python 3.12.
- Do not add a Dockerfile unless the deployment decision changes.
- Keep function code and dependencies in separate ZIP packages.
- Build the Lambda layer under a top-level `python/` directory.
- Do not add API Gateway event parsing unless the integration changes.
- Do not call Kendra for non-HR routes.
- Do not return citations for direct or out-of-scope responses.
- Do not return citations after a guardrail intervention.
- Keep the intent router separate from final answer generation.
- Keep prompts outside the graph nodes where practical.
- Do not log sensitive HR content by default.
- Keep resource IDs and model IDs in Lambda environment variables.
- Test all three intent routes before deployment.

At a minimum, test:

```text
Who are you?
How many sick leave days do I get?
Who won the football match?
```

Also test one known guardrail-blocked request in non-production.

---

## Summary

The current backend flow is:

```text
Chainlit
→ Lambda Python 3.12
→ Input guardrail
→ Claude Sonnet 4.5 AU intent router
→ Kendra only for HR policy requests
→ Claude Sonnet 4.5 AU answer generation
→ Citation filtering
→ Chainlit response
```

The most important rule is:

```text
Only HR policy questions should reach Kendra.
```

Every other request should either be handled directly or stopped before retrieval.