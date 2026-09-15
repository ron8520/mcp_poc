from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import unittest
from unittest.mock import patch


SERVER_MODULE = "servers.sharepoint_mcp.src.server"
TENANT_ID = "11111111-1111-4111-8111-111111111111"
AUDIENCE = "22222222-2222-4222-8222-222222222222"
CALLER_CLIENT_ID = "33333333-3333-4333-8333-333333333333"
SITE_ID = "contoso.sharepoint.com,collection,site-one"
PROVIDER_ARN = (
    "arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:"
    "token-vault/default/oauth2credentialprovider/one"
)


def _native_environment() -> dict[str, str]:
    return {
        "GRAPH_AUTH_MODE": "agentcore_m2m",
        "GRAPH_DRY_RUN": "true",
        "MCP_ENVIRONMENT": "nonprod",
        "MCP_EXECUTION_LANE": "application",
        "MCP_SERVICE_NAME": "sharepoint",
        "APP_ONLY_MAPPING_JSON": json.dumps(
            {
                "schema_version": 1,
                "environment": "nonprod",
                "tenant_id": TENANT_ID,
                "audience": AUDIENCE,
                "target_name": "sharepoint-application",
                "applications": {
                    CALLER_CLIENT_ID: {
                        "provider_arn": PROVIDER_ARN,
                        "grants": {
                            SITE_ID: ["sharepoint_upload_file"],
                        },
                    }
                },
            }
        ),
        "AGENTCORE_WORKLOAD_NAME": "sharepoint-application-nonprod",
    }


def _load_native_server() -> object:
    with patch.dict(os.environ, _native_environment(), clear=True):
        loaded = sys.modules.get(SERVER_MODULE)
        if loaded is None:
            return importlib.import_module(SERVER_MODULE)
        return importlib.reload(loaded)


class FakeContext:
    headers: dict[str, str] = {}


class FakeNativeAuthorization:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls: list[tuple[object, str, str]] = []

    def access_token_for(
        self,
        context: object,
        *,
        site_id: str,
        tool_name: str,
    ) -> str:
        self.events.append("authorize")
        self.calls.append((context, site_id, tool_name))
        return "graph-token"


class FakeGraphClient:
    dry_run = True

    def __init__(self, events: list[str], *, dry_run: bool, access_token: str) -> None:
        events.append("graph_client")
        self.events = events
        self.dry_run = dry_run
        self.access_token = access_token

    def upload_file(
        self,
        site_id: str,
        file_path: str,
        content: str,
        user_assertion: str | None = None,
    ) -> dict[str, object]:
        self.events.append("graph_upload")
        return {
            "site_id": site_id,
            "file_path": file_path,
            "content_length": len(content),
            "user_assertion": user_assertion,
        }


class SharePointServerNativeAuthTest(unittest.TestCase):
    def test_native_upload_authenticates_before_dry_run_graph_call(self) -> None:
        server = _load_native_server()
        events: list[str] = []
        authorization = FakeNativeAuthorization(events)

        def graph_factory(*, dry_run: bool, access_token: str) -> FakeGraphClient:
            return FakeGraphClient(
                events,
                dry_run=dry_run,
                access_token=access_token,
            )

        with (
            patch.object(server, "app_only_authorization", authorization),
            patch.object(server, "SharePointGraphClient", side_effect=graph_factory),
            patch.dict(os.environ, {"GRAPH_DRY_RUN": "true"}),
        ):
            result = server.sharepoint_upload_file(
                SITE_ID,
                "Folder A/report.txt",
                "hello",
                FakeContext(),
            )

        self.assertEqual(events, ["authorize", "graph_client", "graph_upload"])
        self.assertEqual(
            authorization.calls[0][1:],
            (SITE_ID, "sharepoint_upload_file"),
        )
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["result"]["user_assertion"], None)

    def test_public_tool_arguments_remain_unchanged(self) -> None:
        server = _load_native_server()
        expected = {
            "sharepoint_list_site_content": [
                "site_id",
                "correlation_id",
                "ctx",
                "path",
                "recursive",
                "max_items",
            ],
            "sharepoint_get_file_text": [
                "site_id",
                "drive_id",
                "item_id",
                "correlation_id",
                "ctx",
                "max_chars",
            ],
            "sharepoint_upload_file": ["site_id", "file_path", "content", "ctx"],
        }

        for name, parameters in expected.items():
            with self.subTest(name=name):
                self.assertEqual(
                    list(inspect.signature(getattr(server, name)).parameters),
                    parameters,
                )


if __name__ == "__main__":
    unittest.main()
