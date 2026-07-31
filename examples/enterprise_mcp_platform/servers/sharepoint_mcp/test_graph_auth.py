from __future__ import annotations

import os
import unittest
from typing import Any
from unittest.mock import patch

from examples.enterprise_mcp_platform.servers.sharepoint_mcp.src.graph_auth import (
    GraphAuthConfig,
    GraphAuthError,
    GraphTokenProvider,
    user_assertion_from_context,
)


class FakeConfidentialClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.obo_calls: list[tuple[str, list[str]]] = []
        self.app_calls: list[list[str]] = []

    def acquire_token_on_behalf_of(
        self,
        user_assertion: str,
        scopes: list[str],
    ) -> dict[str, Any]:
        self.obo_calls.append((user_assertion, scopes))
        return self.response

    def acquire_token_for_client(self, scopes: list[str]) -> dict[str, Any]:
        self.app_calls.append(scopes)
        return self.response


class GraphTokenProviderTest(unittest.TestCase):
    def test_auth_mode_requires_exact_value(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GRAPH_AUTH_MODE": "OBO",
                "ENTRA_TENANT_ID": "tenant-id",
                "ENTRA_CLIENT_ID": "client-id",
                "ENTRA_CLIENT_SECRET_ARN": "secret-arn",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(GraphAuthError, "must be obo"):
                GraphAuthConfig.from_environment()

    def test_required_environment_rejects_surrounding_whitespace(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GRAPH_AUTH_MODE": "obo",
                "ENTRA_TENANT_ID": " tenant-id ",
                "ENTRA_CLIENT_ID": "client-id",
                "ENTRA_CLIENT_SECRET_ARN": "secret-arn",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(GraphAuthError, "surrounding whitespace"):
                GraphAuthConfig.from_environment()

    def test_header_name_is_preserved_without_cleanup(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GRAPH_AUTH_MODE": "obo",
                "ENTRA_TENANT_ID": "tenant-id",
                "ENTRA_CLIENT_ID": "client-id",
                "ENTRA_CLIENT_SECRET_ARN": "secret-arn",
                "GRAPH_USER_ASSERTION_HEADER": "X-MCP-User-Assertion",
            },
            clear=True,
        ):
            config = GraphAuthConfig.from_environment()

        self.assertEqual(config.user_assertion_header, "X-MCP-User-Assertion")

    def test_obo_uses_gateway_assertion(self) -> None:
        client = FakeConfidentialClient({"access_token": "graph-user-token"})
        provider = GraphTokenProvider(
            _config("obo"),
            secret_loader=lambda _arn, _key: "secret",
            client_factory=lambda _client_id, _authority, _secret: client,
        )

        token = provider.acquire_access_token("mcp-user-token")

        self.assertEqual(token, "graph-user-token")
        self.assertEqual(
            client.obo_calls,
            [("mcp-user-token", ["https://graph.microsoft.com/.default"])],
        )
        self.assertEqual(client.app_calls, [])

    def test_obo_fails_before_loading_secret_without_assertion(self) -> None:
        secret_loads = 0

        def load_secret(_arn: str, _key: str) -> str:
            nonlocal secret_loads
            secret_loads += 1
            return "secret"

        provider = GraphTokenProvider(
            _config("obo"),
            secret_loader=load_secret,
            client_factory=lambda _client_id, _authority, _secret: FakeConfidentialClient(
                {"access_token": "unexpected"}
            ),
        )

        with self.assertRaisesRegex(GraphAuthError, "user assertion"):
            provider.acquire_access_token()
        self.assertEqual(secret_loads, 0)

    def test_client_credentials_does_not_use_user_assertion(self) -> None:
        client = FakeConfidentialClient({"access_token": "graph-app-token"})
        provider = GraphTokenProvider(
            _config("client_credentials"),
            secret_loader=lambda _arn, _key: "secret",
            client_factory=lambda _client_id, _authority, _secret: client,
        )

        token = provider.acquire_access_token()

        self.assertEqual(token, "graph-app-token")
        self.assertEqual(
            client.app_calls,
            [["https://graph.microsoft.com/.default"]],
        )
        self.assertEqual(client.obo_calls, [])

    def test_identity_error_does_not_expose_error_description(self) -> None:
        client = FakeConfidentialClient(
            {
                "error": "invalid_client",
                "error_description": "contains-secret-detail",
                "correlation_id": "abc-123",
            }
        )
        provider = GraphTokenProvider(
            _config("client_credentials"),
            secret_loader=lambda _arn, _key: "secret",
            client_factory=lambda _client_id, _authority, _secret: client,
        )

        with self.assertRaises(GraphAuthError) as raised:
            provider.acquire_access_token()

        self.assertIn("invalid_client", str(raised.exception))
        self.assertIn("abc-123", str(raised.exception))
        self.assertNotIn("contains-secret-detail", str(raised.exception))

    def test_user_assertion_uses_mcp_v2_context_headers(self) -> None:
        class FakeContext:
            headers = {"x-mcp-user-assertion": "gateway-assertion"}

        self.assertEqual(
            user_assertion_from_context(FakeContext()),
            "gateway-assertion",
        )

    def test_user_assertion_does_not_guess_legacy_context_shape(self) -> None:
        class FakeRequest:
            headers = {"x-mcp-user-assertion": "legacy-assertion"}

        class FakeRequestContext:
            request = FakeRequest()

        class FakeContext:
            request_context = FakeRequestContext()

        with self.assertRaises(AttributeError):
            user_assertion_from_context(FakeContext())

    def test_user_assertion_rejects_non_string_header(self) -> None:
        class FakeContext:
            headers = {"x-mcp-user-assertion": 123}

        with self.assertRaisesRegex(GraphAuthError, "must be a string"):
            user_assertion_from_context(FakeContext())


def _config(mode: str) -> GraphAuthConfig:
    return GraphAuthConfig(
        mode=mode,
        tenant_id="tenant-id",
        client_id="client-id",
        client_secret_arn="secret-arn",
    )


if __name__ == "__main__":
    unittest.main()
