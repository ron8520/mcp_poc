# Current PoC: EC2, CodeCommit, ECR, and AgentCore Console

This runbook describes the current single-repository PoC path. It does not
claim that the steps have been completed in AWS or Entra ID.

**PoC sequence:** EC2 workspace → CodeCommit → manual ARM64 image build and
push to ECR → AgentCore Runtime and Gateway configuration in the AWS Console.

CodeCommit and ECR pushes do not trigger a build, Runtime deployment, Gateway
update, or Terraform run. The operator records the source commit and resulting
image digest, then deploys that exact image through the Console. Do not use this
runbook to apply Terraform. The retained Terraform path is one TFE
workspace/state per environment using infra/deployment/; it is a separate
long-term operating model.

## What this stage proves

The repository contains the SharePoint service, Gateway interceptor, Cedar
policy, and infrastructure definitions. Local tests do not prove an ARM64
image build, a live Runtime/Gateway request, Entra token validation, or
Microsoft Graph access. Mark each deployment step complete only after collecting
the stated evidence.

For the first cloud smoke, configure GRAPH_DRY_RUN=true and omit
GRAPH_AUTH_MODE and Graph credentials. Dry-run does not call Microsoft Graph.
Do not set GRAPH_AUTH_MODE=agentcore_m2m for this first pass: that path
authenticates even when Graph dry-run is enabled.

## Values and access to obtain first

Use approved values from the AWS, Entra, and SharePoint owners. Do not guess IDs
or put secret values in this document, Git, shell history, Runtime environment
variables, or logs.

| Value | Source |
| --- | --- |
| AWS account, region, and approved EC2 workspace | AWS/platform owner; use Sydney ap-southeast-2 for this AgentCore PoC. |
| EC2 instance profile / operator role | AWS/platform owner; must grant only the required CodeCommit, ECR, and AgentCore operations. |
| CodeCommit repository and branch | Repository owner. |
| ECR registry and repository | AWS/platform owner; use the approved account and repository. |
| Runtime execution role, VPC subnets/security groups, and Gateway service role | AWS/platform/network owner. Reuse approved resources rather than creating a parallel network. |
| Entra tenant ID and internal-mcp API application client ID | Microsoft identity owner. The API client ID is the v2 access-token audience used here. |
| Test caller application client ID | Microsoft identity owner. This must be a separate client registration from the internal-mcp API resource. |
| Test user and allowed SharePoint site | SharePoint/data owner. Real Graph tests are a separate gate. |

Use an immutable image tag tied to the full CodeCommit commit, and record both
the commit ID and ECR image digest in the deployment notes.

## 1. Prepare the EC2 workspace

Use an approved Linux EC2 workspace in the target AWS account and region. Its
instance profile must be authorized for the selected CodeCommit repository and
ECR repository. It also needs the approved network path to those services.
Prefer an ARM64 workspace or an approved Docker Buildx setup capable of
producing linux/arm64.

Do not expose SSH/RDP to the public internet, add long-lived AWS keys to the
instance, or copy Entra/Graph secrets into the build environment. Confirm which
account and role the session is using:

~~~
aws sts get-caller-identity
aws configure list
~~~

The service listens on 0.0.0.0:8000/mcp in the container. The container must
be built for linux/arm64 for AgentCore Runtime. The currently pinned MCP
Python package is mcp==2.2.0; this package version is not an MCP protocol
version.

## 2. Clone and push source with CodeCommit

In the AWS Console, select or create the approved CodeCommit repository in the
approved region. Configure the EC2 workspace identity for Git access using the
AWS CodeCommit credential guidance; do not put a personal access token or
password into the remote URL.

For a new checkout, install the CodeCommit Git remote helper and clone the
approved repository:

~~~
python3 -m pip install --user git-remote-codecommit
git clone codecommit::<region>://<repository-name>
cd <repository-name>
git status --short
~~~

If the repository is already checked out, verify its remote and branch instead
of cloning another copy. Commit the reviewed source changes and push the
selected branch. Before building, capture the full commit ID:

~~~
git rev-parse HEAD
git status --short
git push origin <branch>
~~~

The working tree should be clean for the image build. Do not commit credentials,
tokens, .env files, or generated secrets.

## 3. Build and publish the ARM64 image to ECR

In the AWS Console, select the approved private ECR repository or create one
only with the platform owner's approval. Confirm the EC2 identity can push to
that repository. Use the full source commit or a unique tag derived from it;
do not publish the PoC as latest.

Authenticate Docker to the approved registry and build from the repository
root so the Dockerfile can access the complete service build context:

~~~
export AWS_REGION=ap-southeast-2
export AWS_ACCOUNT_ID="<approved-account-id>"
export ECR_REPOSITORY="<approved-repository-name>"
export IMAGE_TAG="<full-codecommit-commit-id>"
export ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
export IMAGE_URI="$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

docker buildx build \
  --platform linux/arm64 \
  --load \
  --file servers/sharepoint_mcp/Dockerfile \
  --tag "$IMAGE_URI" \
  .

docker push "$IMAGE_URI"
~~~

If Buildx cannot produce the requested platform, stop and fix the builder; do
not publish an image for a different architecture. Verify the ECR tag and
record its digest:

~~~
aws ecr describe-images \
  --region "$AWS_REGION" \
  --repository-name "$ECR_REPOSITORY" \
  --image-ids imageTag="$IMAGE_TAG" \
  --query 'imageDetails[0].[imageDigest,imagePushedAt]' \
  --output table
~~~

Record the CodeCommit commit ID, ECR repository/tag, image digest, region,
builder architecture, and push time together. An ECR push does not deploy the
image.

## 4. Create or update the AgentCore Runtime in the Console

Use the AgentCore Console in ap-southeast-2. Create a Runtime for the approved
SharePoint service, or update the intended PoC Runtime; do not create an
untracked duplicate. Select the image built in step 3 and verify its digest
matches the recorded ECR artifact.

Use the platform-approved Runtime execution role, VPC subnets, and security
groups. The Runtime role and resource policy must be least-privilege and
separately reviewed. Do not copy Terraform defaults or placeholder IDs into a
live resource. Configure the service's initial dry-run environment with:

- GRAPH_DRY_RUN=true
- no explicit GRAPH_AUTH_MODE
- no Graph client ID, tenant secret, or other Graph credentials

Wait for the Runtime to become ready. Record its ARN, version, image digest, and
Console deployment time. Verify the Runtime process is configured for the
AgentCore contract: ARM64, 0.0.0.0:8000, and /mcp. A ready status alone does
not prove Gateway invocation or Graph behavior.

The current delegated code path uses a Gateway assertion-copy interceptor and
Runtime MSAL OBO. Header forwarding, secret access, a real Entra exchange, and a
real Graph request are separate validation gates; do not add secrets or enable
those paths as part of the first dry-run deployment.

## 5. Register the internal-mcp Entra API resource

In the existing Entra tenant, create or select a single-tenant app registration
named internal-mcp. This registration represents the inbound MCP API; it is
not the client application and is not the downstream Microsoft Graph app.

Configure the API resource:

1. Set access tokens to the v2 format (requestedAccessTokenVersion=2).
2. Expose the delegated scope mcp.invoke.
3. Define the exact app roles used by this API:
   - MCP.SharePoint.Delegated.Read
   - MCP.SharePoint.Delegated.Upload
   - MCP.SharePoint.Application.Read
   - MCP.SharePoint.Application.Upload
4. Add the optional idtyp access-token claim.
5. Set the Enterprise Application's assignment-required control and assign only
   approved test callers to the required scope/role.
6. Record the internal-mcp application client GUID. For v2 access tokens, use
   this GUID as the Gateway audience value.

The API resource registration itself needs no client secret, Microsoft Graph
permission, or redirect URI. An interactive or background caller is a separate
client application. The app-only SharePoint/Graph identity is a third,
downstream registration and must not be confused with the caller.

For the initial smoke, use an approved test caller with a separate client GUID.
The v2 Entra token carries that caller in azp; it is not the API's aud.
Create or adjust the test caller's delegated grant/role assignment through the
identity owner. Do not enable app-only ingress merely to make the first
delegated smoke pass.

## 6. Configure the Gateway in the AgentCore Console

Use the approved shared Gateway or create the PoC Gateway in the same region.
Set its inbound authorization to CUSTOM_JWT using the existing Entra tenant's
v2 discovery metadata:

~~~
https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
~~~

Set the allowed audience to the internal-mcp API client GUID. Restrict the
test client with the exact custom claim rule:

~~~
azp STRING EQUALS <test-caller-client-guid>
~~~

Do not assume AgentCore's allowedClients field checks Entra's azp claim:
the documented field is based on client_id, while this v2 token uses azp.
Keep the explicit claim rule and validate it with a real test token before
expanding the allowed caller set.

Add the SharePoint Runtime as an MCP target. Select the Runtime ARN and approved
version. Configure Gateway-to-Runtime invocation using the Gateway service
role, restricted to the intended Runtime ARN. When entering a Runtime
invocation URL manually, follow AWS's AgentCore MCP-target guidance for the
URL-encoded Runtime ARN and SigV4 service bedrock-agentcore; do not paste the
container's /mcp URL into the Runtime invocation URL field.

Choose and record the MCP protocol version explicitly. These are protocol
dates, not package versions:

| Protocol date | Meaning |
| --- | --- |
| 2026-07-28 | Release-candidate/target date used by the direct client validation path. |
| 2025-11-25 | Current released specification date. |
| 2025-06-18 | Earlier supported protocol date. |
| 2025-03-26 | Earlier supported protocol date. |

AWS's Gateway documentation lists these protocol dates, but older Gateway
resources may have a fixed version unless the account supports updates. Match
the Gateway and Runtime/client behavior; do not claim compatibility from the
SDK version alone. The current package pin is mcp==2.2.0.

Gateway JWT entry validation is not per-tool authorization. Keep Cedar in the
reviewed non-production mode for the initial dry-run and do not send real
SharePoint data until the exact tool grants and negative tests have been
reviewed and the appropriate enforcement mode is approved.

## 7. Smoke-test through the Gateway

Use the approved MCP client path to obtain an Entra token for the internal-mcp
audience, then call the Gateway's MCP URL:

~~~
https://<gateway-id>.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp
~~~

The client sends Authorization: Bearer <Entra access token>. Verify that an
unapproved azp is rejected, the approved test client is accepted, and the
Gateway can list and invoke the expected SharePoint dry-run tools. Do not log
the bearer token. Do not call the IAM-protected Runtime directly with
clients/local_client.py: that client is for an unsigned localhost server, not
a SigV4 Runtime endpoint. A cloud smoke test must use the Gateway plus Entra
token or an explicitly SigV4-capable approved client.

The dry-run result proves only the tested request path and simulated Graph
behavior. It does not prove an OBO exchange, live Graph access, SharePoint ACLs,
application Sites.Selected grants, app-only caller isolation, production
availability, or network controls.

## 8. Keep later identity gates separate

For real delegated Graph access, separately approve and validate the inbound
header allowlist, assertion-copy interceptor, Secrets Manager access, MSAL OBO
configuration, delegated Graph permissions, and employee ACL behavior. Test
success and denial for the intended user and site.

For app-only access, separately approve the caller credential, downstream
Graph application, exact application roles/site grants, Cedar policy and
negative cases. A fixed client-credentials PoC caller does not prove per-app
routing isolation. Native per-app M2M additionally requires its AgentCore
Identity provider, mapping, Runtime IAM boundaries, and live token/Graph
evidence. Native AgentCore Identity OBO and M2M remain target work under
[ADR 0012](adr/0012-agentcore-identity-for-delegated-and-m2m-lanes.md) and
[ADR 0013](adr/0013-staged-entra-app-only-catalog-and-bau-rollout.md).

## Completion record

For each environment, store this non-secret evidence in the approved change
record:

- source repository, branch, and full CodeCommit commit ID
- ECR repository, immutable tag, and image digest
- Runtime ARN/version and the deployed image digest
- Gateway ID/URL, Runtime target ID, region, selected protocol date, and update
  time
- Entra API client GUID, test caller client GUID, and test result summary
- dry-run test results and the remaining Graph/identity/network validation gates

Do not paste access tokens, client secrets, private keys, or document contents
into the change record.

## Official references

- [AWS: MCP protocol contract for AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp-protocol-contract.html)
- [AWS: MCP server targets for AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html)
- [AWS: Create an AgentCore Gateway in the Console](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-create-console.html)
- [AWS: Inbound JWT authorizer](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/inbound-jwt-authorizer.html)
- [AWS: Runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
- [AWS: AgentCore VPC configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html)
- [AWS: CodeCommit Git remote helper](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-git-remote-codecommit.html)
- [AWS: Push an image to Amazon ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html)
- [Microsoft: Expose a web API](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-expose-web-apis)
- [Microsoft Graph: API application resource](https://learn.microsoft.com/en-us/graph/api/resources/apiapplication?view=graph-rest-1.0)
- [Microsoft: Add app roles](https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-app-roles-in-apps)
- [Microsoft: Optional claims](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference)
- [Microsoft: Access-token claims reference](https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference)
- [MCP Python SDK 2.2.0](https://pypi.org/project/mcp/2.2.0/)
