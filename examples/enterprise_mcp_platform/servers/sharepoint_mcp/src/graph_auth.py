from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol


GRAPH_SCOPE = "https://graph.microsoft.com/.default"
DEFAULT_ASSERTION_HEADER = "x-mcp-user-assertion"
SUPPORTED_AUTH_MODES = {"obo", "client_credentials"}


class GraphAuthError(RuntimeError):
    """Raised when downstream Graph credentials cannot be acquired safely."""


class ConfidentialClient(Protocol):
    def acquire_token_on_behalf_of(
        self,
        user_assertion: str,
        scopes: list[str],
    ) -> dict[str, Any]: ...

    def acquire_token_for_client(self, scopes: list[str]) -> dict[str, Any]: ...


SecretLoader = Callable[[str, str], str]
ClientFactory = Callable[[str, str, str], ConfidentialClient]


@dataclass(frozen=True)
class GraphAuthConfig:
    mode: str
    tenant_id: str
    client_id: str
    client_secret_arn: str
    client_secret_json_key: str = "client_secret"
    user_assertion_header: str = DEFAULT_ASSERTION_HEADER

    @classmethod
    def from_environment(cls) -> GraphAuthConfig:
        mode = os.getenv("GRAPH_AUTH_MODE", "")
        if mode not in SUPPORTED_AUTH_MODES:
            raise GraphAuthError(
                "GRAPH_AUTH_MODE must be obo or client_credentials when GRAPH_DRY_RUN is false"
            )

        client_secret_json_key = os.getenv(
            "ENTRA_CLIENT_SECRET_JSON_KEY",
            "client_secret",
        )
        if (
            not client_secret_json_key
            or client_secret_json_key != client_secret_json_key.strip()
        ):
            raise GraphAuthError(
                "ENTRA_CLIENT_SECRET_JSON_KEY must be a non-empty exact value"
            )

        user_assertion_header = os.getenv(
            "GRAPH_USER_ASSERTION_HEADER",
            DEFAULT_ASSERTION_HEADER,
        )
        if (
            not user_assertion_header
            or user_assertion_header != user_assertion_header.strip()
        ):
            raise GraphAuthError(
                "GRAPH_USER_ASSERTION_HEADER must be a non-empty exact value"
            )

        return cls(
            mode=mode,
            tenant_id=_required_environment("ENTRA_TENANT_ID"),
            client_id=_required_environment("ENTRA_CLIENT_ID"),
            client_secret_arn=_required_environment("ENTRA_CLIENT_SECRET_ARN"),
            client_secret_json_key=client_secret_json_key,
            user_assertion_header=user_assertion_header,
        )


class GraphTokenProvider:
    def __init__(
        self,
        config: GraphAuthConfig,
        *,
        secret_loader: SecretLoader | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.config = config
        self._secret_loader = secret_loader or _load_secret
        self._client_factory = client_factory or _create_msal_client
        self._client: ConfidentialClient | None = None

    @classmethod
    def from_environment(cls) -> GraphTokenProvider:
        return cls(GraphAuthConfig.from_environment())

    def acquire_access_token(self, user_assertion: str | None = None) -> str:
        scopes = [GRAPH_SCOPE]
        if self.config.mode == "obo":
            assertion = _validated_assertion(user_assertion)
            result = self._confidential_client().acquire_token_on_behalf_of(
                assertion,
                scopes,
            )
        else:
            result = self._confidential_client().acquire_token_for_client(scopes)

        access_token = result.get("access_token")
        if isinstance(access_token, str) and access_token:
            return access_token

        error = _safe_error_value(result.get("error"), "token_acquisition_failed")
        correlation_id = _safe_error_value(result.get("correlation_id"), "unavailable")
        raise GraphAuthError(
            f"Microsoft Graph token acquisition failed: error={error}, "
            f"correlation_id={correlation_id}"
        )

    def _confidential_client(self) -> ConfidentialClient:
        if self._client is None:
            secret = self._secret_loader(
                self.config.client_secret_arn,
                self.config.client_secret_json_key,
            )
            self._client = self._client_factory(
                self.config.client_id,
                f"https://login.microsoftonline.com/{self.config.tenant_id}",
                secret,
            )
        return self._client


def user_assertion_from_context(
    context: object,
    header_name: str = DEFAULT_ASSERTION_HEADER,
) -> str | None:
    value = context.headers.get(header_name)
    if value is not None and not isinstance(value, str):
        raise GraphAuthError(f"{header_name} must be a string")
    return value


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise GraphAuthError(f"{name} is required when GRAPH_DRY_RUN is false")
    if value != value.strip():
        raise GraphAuthError(f"{name} must not contain surrounding whitespace")
    return value


def _validated_assertion(assertion: str | None) -> str:
    if not isinstance(assertion, str) or not assertion or assertion.isspace():
        raise GraphAuthError("A Gateway-provided user assertion is required for Graph OBO")
    return assertion


def _safe_error_value(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value:
        return fallback
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)[:160]


def _load_secret(secret_arn: str, json_key: str) -> str:
    import boto3

    response = boto3.client("secretsmanager").get_secret_value(SecretId=secret_arn)
    secret_value = response.get("SecretString")
    if not isinstance(secret_value, str):
        secret_binary = response.get("SecretBinary")
        if isinstance(secret_binary, str):
            secret_value = base64.b64decode(secret_binary).decode("utf-8")
        elif isinstance(secret_binary, bytes):
            secret_value = secret_binary.decode("utf-8")

    if not isinstance(secret_value, str) or not secret_value:
        raise GraphAuthError("The configured Entra client secret is empty")

    try:
        parsed = json.loads(secret_value)
    except json.JSONDecodeError:
        return secret_value

    if isinstance(parsed, dict):
        selected = parsed.get(json_key)
        if isinstance(selected, str) and selected:
            return selected
        raise GraphAuthError(
            "The configured Entra secret JSON does not contain the selected key"
        )
    if isinstance(parsed, str) and parsed:
        return parsed
    raise GraphAuthError("The configured Entra client secret has an unsupported format")


def _create_msal_client(
    client_id: str,
    authority: str,
    client_secret: str,
) -> ConfidentialClient:
    import msal

    return msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret,
    )
