import json
import os
from dataclasses import dataclass
from functools import lru_cache

import boto3
import msal


GRAPH_SCOPE = "https://graph.microsoft.com/.default"


def environment(name: str, default: str | None = None) -> str:
    value = os.environ[name] if default is None else os.getenv(name, default)
    if not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty without surrounding whitespace")
    return value


@dataclass(frozen=True)
class Config:
    mode: str
    tenant_id: str
    client_id: str
    secret_arn: str
    secret_key: str
    assertion_header: str

    @classmethod
    def from_environment(cls):
        mode = environment("GRAPH_AUTH_MODE")
        if mode not in {"obo", "client_credentials"}:
            raise ValueError("GRAPH_AUTH_MODE must be obo or client_credentials")
        return cls(
            mode, environment("ENTRA_TENANT_ID"), environment("ENTRA_CLIENT_ID"),
            environment("ENTRA_CLIENT_SECRET_ARN"),
            environment("ENTRA_CLIENT_SECRET_JSON_KEY", "client_secret"),
            environment("GRAPH_USER_ASSERTION_HEADER", "x-mcp-user-assertion"),
        )


def load_secret(config: Config) -> str:
    response = boto3.client("secretsmanager").get_secret_value(SecretId=config.secret_arn)
    if "SecretString" in response:
        value = response["SecretString"]
    else:
        # Boto3 returns decoded bytes for a binary secret.
        value = response["SecretBinary"].decode("utf-8")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    secret = parsed[config.secret_key] if isinstance(parsed, dict) else parsed
    if not isinstance(secret, str) or not secret:
        raise ValueError("The configured Entra client secret must be nonempty text")
    return secret


@lru_cache
def msal_client(config: Config):
    # Secrets are loaded once per process; rotation requires a Runtime recycle.
    return msal.ConfidentialClientApplication(
        config.client_id,
        authority=f"https://login.microsoftonline.com/{config.tenant_id}",
        client_credential=load_secret(config),
    )


def access_token(config: Config, headers) -> str:
    if config.mode == "obo":
        assertion = headers.get(config.assertion_header)
        if not isinstance(assertion, str) or not assertion or assertion.isspace():
            raise PermissionError("A Gateway-provided user assertion is required for Graph OBO")
        result = msal_client(config).acquire_token_on_behalf_of(assertion, [GRAPH_SCOPE])
    else:
        result = msal_client(config).acquire_token_for_client([GRAPH_SCOPE])
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        # MSAL error descriptions can contain identity-provider details.
        raise RuntimeError("Microsoft Graph token acquisition failed")
    return token
