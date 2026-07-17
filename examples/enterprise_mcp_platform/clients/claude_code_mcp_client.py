from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


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

    async with streamablehttp_client(
        mcp_url,
        headers,
        timeout=timedelta(seconds=120),
        terminate_on_close=False,
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print({"tools": [tool.name for tool in getattr(tools, "tools", [])]})

            result = await session.call_tool(
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
