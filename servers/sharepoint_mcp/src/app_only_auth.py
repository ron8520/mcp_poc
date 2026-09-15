from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Mapping, Protocol

import jwt
from pydantic import BaseModel, ConfigDict, Field

from servers.sharepoint_mcp.src.audit import audit


GRAPH_SCOPE = "https://graph.microsoft.com/.default"
CALLER_ASSERTION_HEADER = "x-mcp-caller-assertion"
APPLICATION_TARGET_NAME = "sharepoint-application"
APPLICATION_TOOLS = frozenset(
    {
        "sharepoint_list_site_content",
        "sharepoint_get_file_text",
        "sharepoint_upload_file",
    }
)
READ_ROLE = "MCP.SharePoint.Application.Read"
UPLOAD_ROLE = "MCP.SharePoint.Application.Upload"
GUID_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
ARN_PATTERN = r"^arn:[^\s]+$"

GuidString = Annotated[str, Field(pattern=GUID_PATTERN)]
ProviderArnString = Annotated[str, Field(pattern=ARN_PATTERN)]
SiteIdString = Annotated[str, Field(min_length=1)]
ApplicationToolName = Literal[
    "sharepoint_list_site_content",
    "sharepoint_get_file_text",
    "sharepoint_upload_file",
]
ToolGrant = Annotated[list[ApplicationToolName], Field(min_length=1)]


class AppOnlyAuthError(RuntimeError):
    """Raised when native app-only configuration is invalid."""


class AppOnlyAccessDenied(PermissionError):
    """Raised when a caller is not authorized for an app-only request."""


class AgentCoreClient(Protocol):
    def get_workload_access_token(self, *, workloadName: str) -> dict[str, Any]: ...

    def get_resource_oauth2_token(
        self,
        *,
        workloadIdentityToken: str,
        resourceCredentialProviderName: str,
        scopes: list[str],
        oauth2Flow: str,
    ) -> dict[str, Any]: ...


class ApplicationGrant(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        strict=True,
    )

    provider_arn: ProviderArnString
    grants: dict[SiteIdString, ToolGrant] = Field(min_length=1)


class AppOnlyMapping(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        strict=True,
    )

    schema_version: Literal[1]
    environment: Literal["nonprod", "prod"]
    tenant_id: GuidString
    audience: GuidString
    target_name: Literal["sharepoint-application"]
    applications: dict[GuidString, ApplicationGrant] = Field(min_length=1)

    @classmethod
    def from_json(
        cls,
        value: object,
        *,
        expected_environment: str,
    ) -> AppOnlyMapping:
        parsed = cls.model_validate(value)
        environment = parsed.environment
        if environment != expected_environment:
            raise ValueError(
                "APP_ONLY_MAPPING_JSON environment does not match MCP_ENVIRONMENT"
            )
        return parsed


@dataclass(frozen=True)
class AppOnlyRuntimeConfig:
    mapping: AppOnlyMapping
    workload_name: str
    execution_lane: str = "application"
    service_name: str = "sharepoint"

    @property
    def tenant_id(self) -> str:
        return self.mapping.tenant_id

    @property
    def audience(self) -> str:
        return self.mapping.audience

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @classmethod
    def from_environment(cls) -> AppOnlyRuntimeConfig:
        environment = _required_environment("MCP_ENVIRONMENT")
        if environment not in {"nonprod", "prod"}:
            raise AppOnlyAuthError("MCP_ENVIRONMENT must be nonprod or prod")
        if _required_environment("MCP_EXECUTION_LANE") != "application":
            raise AppOnlyAuthError("MCP_EXECUTION_LANE must be application")
        if _required_environment("MCP_SERVICE_NAME") != "sharepoint":
            raise AppOnlyAuthError("MCP_SERVICE_NAME must be sharepoint")

        mapping_json = _required_environment("APP_ONLY_MAPPING_JSON")
        mapping = AppOnlyMapping.from_json(
            json.loads(mapping_json),
            expected_environment=environment,
        )
        return cls(
            mapping=mapping,
            workload_name=_required_environment("AGENTCORE_WORKLOAD_NAME"),
        )


@dataclass(frozen=True)
class AuthorizedApplicationRequest:
    caller_client_id: str
    site_id: str
    tool_name: str
    provider_arn: str


class AppOnlyJWTValidator:
    def __init__(
        self,
        config: AppOnlyRuntimeConfig,
        *,
        jwks_client: object | None = None,
    ):
        self.config = config
        if jwks_client is None:
            jwks_client = jwt.PyJWKClient(config.jwks_url)
        self._jwks_client = jwks_client

    def validate(self, assertion: str) -> dict[str, Any]:
        if not isinstance(assertion, str) or not assertion or assertion.isspace():
            raise _access_denied()

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(assertion)
            claims = jwt.decode(
                assertion,
                key=signing_key.key,
                algorithms=["RS256"],
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={
                    "require": [
                        "exp",
                        "iss",
                        "aud",
                        "tid",
                        "azp",
                        "idtyp",
                        "ver",
                        "roles",
                    ]
                },
            )
        except jwt.InvalidTokenError:
            raise _access_denied() from None

        if (
            claims.get("ver") != "2.0"
            or claims.get("tid") != self.config.tenant_id
            or claims.get("idtyp") != "app"
            or "scp" in claims
        ):
            raise _access_denied()
        if not isinstance(claims.get("azp"), str):
            raise _access_denied()
        if claims.get("aud") != self.config.audience:
            raise _access_denied()
        if not isinstance(claims.get("roles"), list) or any(
            not isinstance(role, str) for role in claims["roles"]
        ):
            raise _access_denied()
        return claims


class AgentCoreM2MTokenProvider:
    def __init__(
        self,
        config: AppOnlyRuntimeConfig,
        *,
        sdk_client: AgentCoreClient | None = None,
    ) -> None:
        self.config = config
        self._sdk_client = sdk_client

    def acquire_access_token(self, provider_arn: str) -> str:
        client = self._client()
        workload_response = client.get_workload_access_token(
            workloadName=self.config.workload_name,
        )
        workload_identity_token = workload_response["workloadAccessToken"]
        provider_name = provider_arn.rsplit("/", 1)[-1]
        resource_response = client.get_resource_oauth2_token(
            workloadIdentityToken=workload_identity_token,
            resourceCredentialProviderName=provider_name,
            scopes=[GRAPH_SCOPE],
            oauth2Flow="M2M",
        )
        return resource_response["accessToken"]

    def _client(self) -> AgentCoreClient:
        if self._sdk_client is None:
            import boto3

            self._sdk_client = boto3.client("bedrock-agentcore")
        return self._sdk_client


class AppOnlyAuthorization:
    def __init__(
        self,
        config: AppOnlyRuntimeConfig,
        *,
        jwks_client: object | None = None,
        sdk_client: AgentCoreClient | None = None,
    ) -> None:
        self.config = config
        self._validator = AppOnlyJWTValidator(config, jwks_client=jwks_client)
        self._token_provider = AgentCoreM2MTokenProvider(
            config,
            sdk_client=sdk_client,
        )

    @classmethod
    def from_environment(cls) -> AppOnlyAuthorization:
        return cls(AppOnlyRuntimeConfig.from_environment())

    def authorize(
        self,
        context: object,
        *,
        site_id: str,
        tool_name: str,
    ) -> AuthorizedApplicationRequest:
        if tool_name not in APPLICATION_TOOLS:
            raise _access_denied()
        assertion = caller_assertion_from_context(context)
        claims = self._validator.validate(assertion)
        caller_client_id = claims["azp"]
        application = self.config.mapping.applications.get(caller_client_id)
        if application is None:
            raise _access_denied()
        granted_tools = application.grants.get(site_id)
        if granted_tools is None or tool_name not in granted_tools:
            raise _access_denied()

        required_role = (
            UPLOAD_ROLE if tool_name == "sharepoint_upload_file" else READ_ROLE
        )
        if required_role not in claims["roles"]:
            raise _access_denied()
        audit(
            "auth.app_only",
            "",
            "authorized",
            caller_client_id=caller_client_id,
            site_id=site_id,
            tool_name=tool_name,
            provider_arn=application.provider_arn,
        )
        return AuthorizedApplicationRequest(
            caller_client_id=caller_client_id,
            site_id=site_id,
            tool_name=tool_name,
            provider_arn=application.provider_arn,
        )

    def access_token_for(
        self,
        context: object,
        *,
        site_id: str,
        tool_name: str,
    ) -> str:
        authorization = self.authorize(
            context,
            site_id=site_id,
            tool_name=tool_name,
        )
        return self._token_provider.acquire_access_token(authorization.provider_arn)


def caller_assertion_from_context(context: object) -> str:
    headers = getattr(context, "headers", None)
    if not isinstance(headers, Mapping):
        raise _access_denied()
    value = headers.get(CALLER_ASSERTION_HEADER)
    if not isinstance(value, str) or not value or value.isspace():
        raise _access_denied()
    return value


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise AppOnlyAuthError(f"{name} is required in native app-only mode")
    if value != value.strip():
        raise AppOnlyAuthError(f"{name} must not contain surrounding whitespace")
    return value


def _access_denied() -> AppOnlyAccessDenied:
    return AppOnlyAccessDenied("App-only access denied")
