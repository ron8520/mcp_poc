from __future__ import annotations

import importlib
import os
import sys
import unittest
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from unittest.mock import patch

import httpx2
from mcp import CallToolResult, Client, ListToolsResult
from mcp.client.streamable_http import streamable_http_client


SERVER_MODULE = "servers.sharepoint_mcp.src.server"
SITE_ID = "contoso.sharepoint.com,collection,site-one"


def _load_dry_run_server() -> Any:
    with patch.dict(os.environ, {"GRAPH_DRY_RUN": "true"}, clear=True):
        loaded = sys.modules.get(SERVER_MODULE)
        if loaded is None:
            return importlib.import_module(SERVER_MODULE)
        return importlib.reload(loaded)


@asynccontextmanager
async def _wire_client(
    server: Any,
    *,
    headers: dict[str, str] | None = None,
) -> AsyncIterator[Client]:
    app = server.mcp.streamable_http_app(stateless_http=True, host="0.0.0.0")
    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(
            base_url="http://testserver",
            headers=headers,
            transport=httpx2.ASGITransport(app=app),
        ) as http_client:
            transport = streamable_http_client(
                "http://testserver/mcp",
                http_client=http_client,
                terminate_on_close=False,
            )
            async with Client(transport, mode="2026-07-28") as client:
                yield client


class HeaderCapturingGraph:
    dry_run = True
    user_assertion_header = "x-mcp-user-assertion"

    def __init__(self) -> None:
        self.user_assertion: str | None = None

    def upload_file(
        self,
        site_id: str,
        file_path: str,
        content: str,
        user_assertion: str | None = None,
    ) -> dict[str, str]:
        self.user_assertion = user_assertion
        return {"site_id": site_id, "file_path": file_path, "status": "dry_run"}


class HeaderCapturingAuthorization:
    def __init__(self) -> None:
        self.caller_assertion: str | None = None

    def access_token_for(
        self,
        context: Any,
        *,
        site_id: str,
        tool_name: str,
    ) -> str:
        self.caller_assertion = context.headers.get("x-mcp-caller-assertion")
        return "graph-token"


class SharePointSDK2WireTest(unittest.IsolatedAsyncioTestCase):
    async def test_streamable_http_tools_and_tool_results_use_sdk2_types(self) -> None:
        server = _load_dry_run_server()

        async with _wire_client(server) as client:
            tools = await client.list_tools()
            self.assertIsInstance(tools, ListToolsResult)
            self.assertEqual(
                [tool.name for tool in tools.tools],
                [
                    "sharepoint_list_site_content",
                    "sharepoint_get_file_text",
                    "sharepoint_upload_file",
                ],
            )

            result = await client.call_tool(
                "sharepoint_upload_file",
                {
                    "site_id": SITE_ID,
                    "file_path": "Folder/report.txt",
                    "content": "hello",
                },
            )
            self.assertIsInstance(result, CallToolResult)
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["status"], "dry_run")
            self.assertEqual(
                result.structured_content["result"]["status"],
                "dry_run",
            )

            invalid = await client.call_tool(
                "sharepoint_upload_file",
                {
                    "site_id": SITE_ID,
                    "file_path": "../report.txt",
                    "content": "hello",
                },
            )
            self.assertIsInstance(invalid, CallToolResult)
            self.assertTrue(invalid.is_error)
            self.assertIsNone(invalid.structured_content)
            self.assertEqual(
                invalid.content[0].text,
                "Error executing tool sharepoint_upload_file",
            )

    async def test_wire_context_forwards_delegated_assertion_header(self) -> None:
        server = _load_dry_run_server()
        graph = HeaderCapturingGraph()
        with patch.object(server, "graph", graph):
            async with _wire_client(
                server,
                headers={"x-mcp-user-assertion": "delegated-assertion"},
            ) as client:
                result = await client.call_tool(
                    "sharepoint_upload_file",
                    {
                        "site_id": SITE_ID,
                        "file_path": "report.txt",
                        "content": "hello",
                    },
                )

        self.assertFalse(result.is_error)
        self.assertEqual(graph.user_assertion, "delegated-assertion")

    async def test_wire_context_forwards_native_caller_assertion_header(self) -> None:
        server = _load_dry_run_server()
        authorization = HeaderCapturingAuthorization()

        def graph_factory(*, dry_run: bool, access_token: str) -> HeaderCapturingGraph:
            self.assertTrue(dry_run)
            self.assertEqual(access_token, "graph-token")
            return HeaderCapturingGraph()

        with (
            patch.object(server, "app_only_authorization", authorization),
            patch.object(server, "SharePointGraphClient", side_effect=graph_factory),
        ):
            async with _wire_client(
                server,
                headers={"x-mcp-caller-assertion": "native-assertion"},
            ) as client:
                result = await client.call_tool(
                    "sharepoint_upload_file",
                    {
                        "site_id": SITE_ID,
                        "file_path": "report.txt",
                        "content": "hello",
                    },
                )

        self.assertFalse(result.is_error)
        self.assertEqual(authorization.caller_assertion, "native-assertion")


if __name__ == "__main__":
    unittest.main()
