from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

import boto3
import jwt


CALLER_ASSERTION_HEADER = "x-mcp-caller-assertion"
ROLE = "MCP.CRM.Case.Summary.Update"
GUID_PATTERN = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
PROVIDER_ARN_PATTERN = (
    r"arn:aws:bedrock-agentcore:[a-z0-9-]+:[0-9]{12}:"
    r"token-vault/[^/]+/oauth2credentialprovider/[A-Za-z0-9_-]+"
)


def _required(name: str) -> str:
    value = os.environ[name]
    if not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty without surrounding whitespace")
    return value


def require_guid(value: object) -> None:
    if not isinstance(value, str) or not re.fullmatch(GUID_PATTERN, value):
        raise ValueError("Expected a GUID")


@dataclass(frozen=True)
class CRMConfig:
    base_url: str
    summary_field: str
    max_chars: int
    tenant_id: str
    audience: str
    caller_cases: dict[str, list[str]]
    workload_name: str
    provider_arn: str

    def __post_init__(self) -> None:
        if not re.fullmatch(
            r"https://[a-z0-9-]+\.crm[0-9]*\.dynamics\.com",
            self.base_url,
        ):
            raise ValueError(
                "CRM_BASE_URL must be a Dataverse HTTPS origin without a trailing slash"
            )
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.summary_field):
            raise ValueError("CRM_SUMMARY_FIELD must be a column logical name")
        if type(self.max_chars) is not int or not 1 <= self.max_chars <= 1048576:
            raise ValueError("CRM_SUMMARY_MAX_CHARS must be between 1 and 1048576")
        require_guid(self.tenant_id)
        require_guid(self.audience)
        if not isinstance(self.caller_cases, dict) or not self.caller_cases:
            raise ValueError("CRM_CALLER_CASES_JSON must contain caller-to-case grants")
        for caller, cases in self.caller_cases.items():
            require_guid(caller)
            if not isinstance(cases, list) or not cases:
                raise ValueError("Each caller requires a nonempty case GUID list")
            for case_id in cases:
                require_guid(case_id)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.workload_name):
            raise ValueError("Invalid AGENTCORE_WORKLOAD_NAME")
        if not re.fullmatch(PROVIDER_ARN_PATTERN, self.provider_arn):
            raise ValueError(
                "CRM_OAUTH_PROVIDER_ARN must identify an OAuth2 credential provider"
            )

    @classmethod
    def from_environment(cls) -> CRMConfig:
        return cls(
            base_url=_required("CRM_BASE_URL"),
            summary_field=_required("CRM_SUMMARY_FIELD"),
            max_chars=int(_required("CRM_SUMMARY_MAX_CHARS")),
            tenant_id=_required("CRM_CALLER_TENANT_ID"),
            audience=_required("CRM_CALLER_AUDIENCE"),
            caller_cases=json.loads(_required("CRM_CALLER_CASES_JSON")),
            workload_name=_required("AGENTCORE_WORKLOAD_NAME"),
            provider_arn=_required("CRM_OAUTH_PROVIDER_ARN"),
        )


@lru_cache(maxsize=None)
def jwks_client(tenant_id: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    )


@lru_cache(maxsize=None)
def identity_client(region: str):
    return boto3.client("bedrock-agentcore", region_name=region)


def authorize(config: CRMConfig, headers: Mapping[str, str], case_id: str) -> str:
    assertion = headers.get(CALLER_ASSERTION_HEADER)
    if not isinstance(assertion, str) or not assertion or assertion.isspace():
        raise PermissionError("CRM app-only access denied")
    try:
        signing_key = jwks_client(config.tenant_id).get_signing_key_from_jwt(assertion)
        claims = jwt.decode(
            assertion,
            signing_key.key,
            algorithms=["RS256"],
            audience=config.audience,
            issuer=f"https://login.microsoftonline.com/{config.tenant_id}/v2.0",
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
        raise PermissionError("CRM app-only access denied") from None

    caller = claims["azp"]
    roles = claims["roles"]
    if (
        claims["tid"] != config.tenant_id
        or claims["aud"] != config.audience
        or claims["idtyp"] != "app"
        or claims["ver"] != "2.0"
        or "scp" in claims
        or not isinstance(caller, str)
        or not isinstance(roles, list)
        or any(not isinstance(role, str) for role in roles)
        or ROLE not in roles
        or case_id not in config.caller_cases.get(caller, [])
    ):
        raise PermissionError("CRM app-only access denied")
    return caller


def access_token(config: CRMConfig) -> str:
    region = config.provider_arn.split(":", 5)[3]
    provider_name = config.provider_arn.rsplit("/", 1)[1]
    client = identity_client(region)
    workload = client.get_workload_access_token(
        workloadName=config.workload_name,
    )
    result = client.get_resource_oauth2_token(
        workloadIdentityToken=workload["workloadAccessToken"],
        resourceCredentialProviderName=provider_name,
        scopes=[f"{config.base_url}/.default"],
        oauth2Flow="M2M",
    )
    token = result["accessToken"]
    if not isinstance(token, str) or not token:
        raise RuntimeError("CRM token provider returned an empty access token")
    return token
