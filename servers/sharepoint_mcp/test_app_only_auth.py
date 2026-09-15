from __future__ import annotations

import io
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from servers.sharepoint_mcp.src.app_only_auth import (
    APPLICATION_TOOLS,
    AppOnlyAccessDenied,
    AppOnlyAuthorization,
    AppOnlyMapping,
    AppOnlyRuntimeConfig,
    AgentCoreM2MTokenProvider,
)


TENANT_ID = "11111111-1111-4111-8111-111111111111"
AUDIENCE = "22222222-2222-4222-8222-222222222222"
CALLER_ONE = "33333333-3333-4333-8333-333333333333"
CALLER_TWO = "44444444-4444-4444-8444-444444444444"
UNKNOWN_CALLER = "55555555-5555-4555-8555-555555555555"
SITE_ONE = "contoso.sharepoint.com,collection,site-one"
SITE_TWO = "contoso.sharepoint.com,collection,site-two"
PROVIDER_ONE = (
    "arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:"
    "token-vault/default/oauth2credentialprovider/one"
)
PROVIDER_TWO = (
    "arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:"
    "token-vault/default/oauth2credentialprovider/two"
)


class FakeContext:
    def __init__(self, token: str) -> None:
        self.headers = {"x-mcp-caller-assertion": token}


class FakeJwksClient:
    def __init__(self, public_key: object) -> None:
        self.public_key = public_key
        self.calls: list[str] = []

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        self.calls.append(token)
        return SimpleNamespace(key=self.public_key)


class FailingJwksClient:
    def __init__(self, failure: Exception) -> None:
        self.failure = failure

    def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
        raise self.failure


class FakeAgentCoreClient:
    def __init__(self) -> None:
        self.workload_calls: list[dict[str, str]] = []
        self.resource_calls: list[dict[str, object]] = []

    def get_workload_access_token(self, **kwargs: str) -> dict[str, str]:
        self.workload_calls.append(kwargs)
        return {"workloadAccessToken": "workload-token"}

    def get_resource_oauth2_token(self, **kwargs: object) -> dict[str, str]:
        self.resource_calls.append(kwargs)
        provider_name = kwargs["resourceCredentialProviderName"]
        return {"accessToken": f"graph-token-{provider_name}"}


class ConcurrentAgentCoreClient(FakeAgentCoreClient):
    def __init__(self) -> None:
        super().__init__()
        self._barrier = threading.Barrier(2)

    def get_workload_access_token(self, **kwargs: str) -> dict[str, str]:
        self._barrier.wait()
        workload_token = f"workload-token-{threading.get_ident()}"
        self.workload_calls.append(kwargs)
        return {"workloadAccessToken": workload_token}

    def get_resource_oauth2_token(self, **kwargs: object) -> dict[str, str]:
        self.resource_calls.append(kwargs)
        provider_name = kwargs["resourceCredentialProviderName"]
        workload_token = kwargs["workloadIdentityToken"]
        return {"accessToken": f"graph-token-{provider_name}-{workload_token}"}


class FailingAgentCoreClient:
    def __init__(self, failure: Exception) -> None:
        self.failure = failure
        self.workload_calls = 0
        self.resource_calls = 0

    def get_workload_access_token(self, **_kwargs: str) -> dict[str, str]:
        self.workload_calls += 1
        raise self.failure

    def get_resource_oauth2_token(self, **_kwargs: object) -> dict[str, str]:
        self.resource_calls += 1
        raise self.failure


def _mapping_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "environment": "nonprod",
        "tenant_id": TENANT_ID,
        "audience": AUDIENCE,
        "target_name": "sharepoint-application",
        "applications": {
            CALLER_ONE: {
                "provider_arn": PROVIDER_ONE,
                "grants": {
                    SITE_ONE: ["sharepoint_list_site_content"],
                },
            },
            CALLER_TWO: {
                "provider_arn": PROVIDER_TWO,
                "grants": {
                    SITE_TWO: ["sharepoint_upload_file"],
                },
            },
        },
    }


def _config() -> AppOnlyRuntimeConfig:
    return AppOnlyRuntimeConfig(
        mapping=AppOnlyMapping.from_json(
            _mapping_data(),
            expected_environment="nonprod",
        ),
        workload_name="sharepoint-application-nonprod",
    )


class AppOnlyAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()

    def _token(self, caller: str = CALLER_ONE, **claims: object) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, object] = {
            "ver": "2.0",
            "iss": _config().issuer,
            "aud": AUDIENCE,
            "tid": TENANT_ID,
            "azp": caller,
            "idtyp": "app",
            "roles": [
                "MCP.SharePoint.Application.Read",
                "MCP.SharePoint.Application.Upload",
            ],
            "exp": now + timedelta(minutes=5),
        }
        payload.update(claims)
        return jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    def _authorization(
        self,
        sdk_client: FakeAgentCoreClient | None = None,
    ) -> AppOnlyAuthorization:
        return AppOnlyAuthorization(
            _config(),
            jwks_client=FakeJwksClient(self.public_key),
            sdk_client=sdk_client,
        )

    def test_mapping_is_strict_and_tied_to_runtime_environment(self) -> None:
        with self.assertRaises(ValidationError):
            AppOnlyMapping.from_json(
                {**_mapping_data(), "unexpected": True},
                expected_environment="nonprod",
            )
        with self.assertRaises(ValueError):
            AppOnlyMapping.from_json(
                _mapping_data(),
                expected_environment="prod",
            )

    def test_runtime_environment_requires_native_lane_contract(self) -> None:
        mapping_json = json.dumps(_mapping_data())
        with patch.dict(
            os.environ,
            {
                "MCP_ENVIRONMENT": "nonprod",
                "MCP_EXECUTION_LANE": "application",
                "MCP_SERVICE_NAME": "sharepoint",
                "APP_ONLY_MAPPING_JSON": mapping_json,
                "AGENTCORE_WORKLOAD_NAME": "sharepoint-application-nonprod",
            },
            clear=True,
        ):
            config = AppOnlyRuntimeConfig.from_environment()

        self.assertEqual(config.mapping.target_name, "sharepoint-application")
        self.assertEqual(
            config.issuer,
            f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        )
        self.assertIn(TENANT_ID, config.jwks_url)

    def test_agentcore_token_adapter_uses_selected_provider_and_m2m(self) -> None:
        client = FakeAgentCoreClient()
        token = AgentCoreM2MTokenProvider(
            _config(),
            sdk_client=client,
        ).acquire_access_token(PROVIDER_TWO)

        self.assertEqual(token, "graph-token-two")
        self.assertEqual(
            client.workload_calls,
            [{"workloadName": "sharepoint-application-nonprod"}],
        )
        self.assertEqual(
            client.resource_calls,
            [
                {
                    "workloadIdentityToken": "workload-token",
                    "resourceCredentialProviderName": "two",
                    "scopes": ["https://graph.microsoft.com/.default"],
                    "oauth2Flow": "M2M",
                }
            ],
        )

    def test_two_callers_select_only_their_exact_site_action_and_provider(self) -> None:
        sdk_client = FakeAgentCoreClient()
        authorization = self._authorization(sdk_client)

        assertion_one = self._token(CALLER_ONE)
        audit_output = io.StringIO()
        with redirect_stdout(audit_output):
            token_one = authorization.access_token_for(
                FakeContext(assertion_one),
                site_id=SITE_ONE,
                tool_name="sharepoint_list_site_content",
            )
            token_two = authorization.access_token_for(
                FakeContext(self._token(CALLER_TWO)),
                site_id=SITE_TWO,
                tool_name="sharepoint_upload_file",
            )

        self.assertEqual(token_one, "graph-token-one")
        self.assertEqual(token_two, "graph-token-two")
        events = [json.loads(line) for line in audit_output.getvalue().splitlines()]
        self.assertEqual(events[0]["caller_client_id"], CALLER_ONE)
        self.assertEqual(events[0]["provider_arn"], PROVIDER_ONE)
        self.assertEqual(events[0]["site_id"], SITE_ONE)
        self.assertEqual(events[0]["tool_name"], "sharepoint_list_site_content")
        self.assertNotIn(assertion_one, audit_output.getvalue())
        self.assertNotIn("workload-token", audit_output.getvalue())
        self.assertNotIn("graph-token-one", audit_output.getvalue())
        self.assertEqual(
            [
                call["resourceCredentialProviderName"]
                for call in sdk_client.resource_calls
            ],
            ["one", "two"],
        )

        with self.assertRaises(AppOnlyAccessDenied):
            authorization.access_token_for(
                FakeContext(self._token(CALLER_ONE)),
                site_id=SITE_ONE,
                tool_name="sharepoint_upload_file",
            )
        with self.assertRaises(AppOnlyAccessDenied):
            authorization.access_token_for(
                FakeContext(self._token(CALLER_ONE)),
                site_id=SITE_TWO,
                tool_name="sharepoint_list_site_content",
            )
        self.assertEqual(len(sdk_client.resource_calls), 2)

    def test_concurrent_callers_keep_workload_and_graph_tokens_isolated(self) -> None:
        sdk_client = ConcurrentAgentCoreClient()
        authorization = self._authorization(sdk_client)
        requests = (
            (CALLER_ONE, SITE_ONE, "sharepoint_list_site_content", "one"),
            (CALLER_TWO, SITE_TWO, "sharepoint_upload_file", "two"),
        )

        def acquire(request: tuple[str, str, str, str]) -> str:
            caller, site_id, tool_name, _provider_name = request
            return authorization.access_token_for(
                FakeContext(self._token(caller)),
                site_id=site_id,
                tool_name=tool_name,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            tokens = list(executor.map(acquire, requests))

        self.assertIn("graph-token-one-workload-token-", tokens[0])
        self.assertIn("graph-token-two-workload-token-", tokens[1])
        self.assertNotEqual(
            tokens[0].split("-workload-token-")[0],
            tokens[1].split("-workload-token-")[0],
        )
        for call in sdk_client.resource_calls:
            provider_name = str(call["resourceCredentialProviderName"])
            self.assertTrue(
                str(call["workloadIdentityToken"]).startswith("workload-token-")
            )
            expected_token = (
                f"graph-token-{provider_name}-{call['workloadIdentityToken']}"
            )
            self.assertIn(expected_token, tokens)

    def test_denied_tokens_and_callers_do_not_reach_agentcore(self) -> None:
        sdk_client = FakeAgentCoreClient()
        authorization = self._authorization(sdk_client)
        denied_tokens = (
            self._token(exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
            self._token(tid="99999999-9999-4999-8999-999999999999"),
            self._token(aud="99999999-9999-4999-8999-999999999999"),
            self._token(idtyp="user", scp="MCP.SharePoint.Application.Read"),
            self._token(caller=UNKNOWN_CALLER),
        )

        for token in denied_tokens:
            with self.subTest(token=token):
                with self.assertRaises(AppOnlyAccessDenied) as raised:
                    authorization.access_token_for(
                        FakeContext(token),
                        site_id=SITE_ONE,
                        tool_name="sharepoint_list_site_content",
                    )
                self.assertEqual(str(raised.exception), "App-only access denied")

        with self.assertRaises(AppOnlyAccessDenied):
            authorization.access_token_for(
                FakeContext("not-a-jwt"),
                site_id=SITE_ONE,
                tool_name="sharepoint_list_site_content",
            )
        self.assertEqual(sdk_client.workload_calls, [])
        self.assertEqual(sdk_client.resource_calls, [])

    def test_jwks_connection_failure_propagates_without_reaching_agentcore(
        self,
    ) -> None:
        failure = jwt.PyJWKClientConnectionError("JWKS endpoint unavailable")
        sdk_client = FakeAgentCoreClient()
        authorization = AppOnlyAuthorization(
            _config(),
            jwks_client=FailingJwksClient(failure),
            sdk_client=sdk_client,
        )

        with self.assertRaises(jwt.PyJWKClientConnectionError) as raised:
            authorization.access_token_for(
                FakeContext(self._token()),
                site_id=SITE_ONE,
                tool_name="sharepoint_list_site_content",
            )

        self.assertIs(raised.exception, failure)
        self.assertEqual(sdk_client.workload_calls, [])
        self.assertEqual(sdk_client.resource_calls, [])

    def test_missing_required_application_role_is_denied_before_broker(self) -> None:
        sdk_client = FakeAgentCoreClient()
        authorization = self._authorization(sdk_client)
        token = self._token(roles=["MCP.SharePoint.Application.Upload"])

        with self.assertRaises(AppOnlyAccessDenied):
            authorization.access_token_for(
                FakeContext(token),
                site_id=SITE_ONE,
                tool_name="sharepoint_list_site_content",
            )
        self.assertEqual(sdk_client.workload_calls, [])

    def test_missing_or_malformed_caller_assertion_is_denied_before_broker(
        self,
    ) -> None:
        sdk_client = FakeAgentCoreClient()
        authorization = self._authorization(sdk_client)

        for context in (
            SimpleNamespace(headers={}),
            SimpleNamespace(),
            FakeContext(" "),
        ):
            with self.subTest(context=context), self.assertRaises(AppOnlyAccessDenied):
                authorization.access_token_for(
                    context,
                    site_id=SITE_ONE,
                    tool_name="sharepoint_list_site_content",
        )

        for roles in (None, "MCP.SharePoint.Application.Read", [1]):
            token = self._token(roles=roles)
            with self.subTest(roles=roles), self.assertRaises(AppOnlyAccessDenied):
                authorization.access_token_for(
                    FakeContext(token),
                    site_id=SITE_ONE,
                    tool_name="sharepoint_list_site_content",
                )

        self.assertEqual(sdk_client.workload_calls, [])

    def test_agentcore_workload_failure_propagates_without_wrapping(self) -> None:
        failure = RuntimeError("agentcore workload failure")
        sdk_client = FailingAgentCoreClient(failure)
        authorization = self._authorization(sdk_client)  # type: ignore[arg-type]

        with self.assertRaisesRegex(
            RuntimeError,
            "agentcore workload failure",
        ) as raised:
            authorization.access_token_for(
                FakeContext(self._token()),
                site_id=SITE_ONE,
                tool_name="sharepoint_list_site_content",
            )

        self.assertIs(raised.exception, failure)
        self.assertEqual(sdk_client.workload_calls, 1)
        self.assertEqual(sdk_client.resource_calls, 0)

    def test_supported_tools_are_exactly_the_local_tool_names(self) -> None:
        self.assertEqual(
            APPLICATION_TOOLS,
            {
                "sharepoint_list_site_content",
                "sharepoint_get_file_text",
                "sharepoint_upload_file",
            },
        )


if __name__ == "__main__":
    unittest.main()
