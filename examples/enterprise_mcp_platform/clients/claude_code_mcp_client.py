from __future__ import annotations

import asyncio
import os
import sys

import httpx2
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


async def main() -> None:
    mcp_url = _required_env("ENTERPRISE_MCP_URL")
    token = _required_env("ENTRA_ACCESS_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "x-correlation-id": os.getenv("CORRELATION_ID", "claude-code-example-001"),
    }

    async with httpx2.AsyncClient(
        headers=headers,
        timeout=httpx2.Timeout(120.0),
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client(
            mcp_url,
            http_client=http_client,
            terminate_on_close=False,
        )
        async with Client(
            transport,
            mode="legacy",
            read_timeout_seconds=120,
        ) as client:
            tools = await client.list_tools()
            print({"tools": [tool.name for tool in getattr(tools, "tools", [])]})

            result = await client.call_tool(
                "sharepoint_get_file_text",
                {
                    "site_id": "engineering-site",
                    "drive_id": "drive-id",
                    "item_id": "item-id",
                    "max_chars": 4000,
                    "correlation_id": "claude-code-example-001",
                },
            )
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
