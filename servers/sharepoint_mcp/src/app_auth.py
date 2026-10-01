import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Literal

import boto3
import jwt
from pydantic import BaseModel, ConfigDict, Field

from servers.sharepoint_mcp.src.audit import audit
from servers.sharepoint_mcp.src.auth import GRAPH_SCOPE, environment


Guid = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")]
ToolName = Literal["sharepoint_list_site_content", "sharepoint_get_file_text", "sharepoint_upload_file"]


class Application(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)
    provider_arn: Annotated[str, Field(pattern=r"^arn:[^\s]+$")]
    grants: dict[Annotated[str, Field(min_length=1)], Annotated[list[ToolName], Field(min_length=1)]] = Field(min_length=1)


class Mapping(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)
    schema_version: Literal[1]
    environment: Literal["nonprod", "prod"]
    tenant_id: Guid
    audience: Guid
    target_name: Literal["sharepoint-application"]
    applications: dict[Guid, Application] = Field(min_length=1)


@dataclass(frozen=True)
class Config:
    mapping: Mapping
    workload_name: str

    @classmethod
    def from_environment(cls):
        mapping = Mapping.model_validate(json.loads(environment("APP_ONLY_MAPPING_JSON")))
        if mapping.environment != environment("MCP_ENVIRONMENT"):
            raise ValueError("APP_ONLY_MAPPING_JSON environment does not match MCP_ENVIRONMENT")
        if environment("MCP_EXECUTION_LANE") != "application":
            raise ValueError("MCP_EXECUTION_LANE must be application")
        if environment("MCP_SERVICE_NAME") != "sharepoint":
            raise ValueError("MCP_SERVICE_NAME must be sharepoint")
        return cls(mapping, environment("AGENTCORE_WORKLOAD_NAME"))


@lru_cache
def jwks_client(tenant_id: str):
    return jwt.PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys")


@lru_cache
def identity_client():
    return boto3.client("bedrock-agentcore")


def authorize(config: Config, headers, site_id: str, tool_name: str) -> str:
    mapping = config.mapping
    assertion = headers.get("x-mcp-caller-assertion")
    if not isinstance(assertion, str) or not assertion or assertion.isspace():
        raise PermissionError("App-only access denied")
    try:
        key = jwks_client(mapping.tenant_id).get_signing_key_from_jwt(assertion).key
        claims = jwt.decode(
            assertion, key, algorithms=["RS256"], audience=mapping.audience,
            issuer=f"https://login.microsoftonline.com/{mapping.tenant_id}/v2.0",
            options={"require": ["exp", "iss", "aud", "tid", "azp", "idtyp", "ver", "roles"]},
        )
    except jwt.InvalidTokenError:
        raise PermissionError("App-only access denied") from None
    caller = claims["azp"]
    roles = claims["roles"]
    if (claims["tid"] != mapping.tenant_id or claims["aud"] != mapping.audience
            or claims["idtyp"] != "app" or claims["ver"] != "2.0" or "scp" in claims
            or not isinstance(caller, str) or not isinstance(roles, list)
            or any(not isinstance(role, str) for role in roles)):
        raise PermissionError("App-only access denied")
    application = mapping.applications.get(caller)
    if application is None or tool_name not in application.grants.get(site_id, []):
        raise PermissionError("App-only access denied")
    role = "MCP.SharePoint.Application.Upload" if tool_name == "sharepoint_upload_file" else "MCP.SharePoint.Application.Read"
    if role not in roles:
        raise PermissionError("App-only access denied")
    audit("auth.app_only", "", "authorized", caller_client_id=caller,
          site_id=site_id, tool_name=tool_name, provider_arn=application.provider_arn)
    return application.provider_arn


def access_token(config: Config, provider_arn: str) -> str:
    client = identity_client()
    workload = client.get_workload_access_token(workloadName=config.workload_name)
    response = client.get_resource_oauth2_token(
        workloadIdentityToken=workload["workloadAccessToken"],
        resourceCredentialProviderName=provider_arn.rsplit("/", 1)[-1],
        scopes=[GRAPH_SCOPE], oauth2Flow="M2M",
    )
    return response["accessToken"]
