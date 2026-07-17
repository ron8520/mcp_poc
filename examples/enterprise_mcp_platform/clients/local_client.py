from __future__ import annotations

import asyncio
import os
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> None:
    mcp_url = os.getenv("MCP_URL", "http://localhost:8000/mcp")

    async with streamablehttp_client(
        mcp_url,
        {},
        timeout=timedelta(seconds=120),
        terminate_on_close=False,
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print({"tools": [tool.name for tool in getattr(tools, "tools", [])]})

            result = await session.call_tool(
                "sharepoint_list_site_content",
                {
                    "site_id": "hr-policy-site",
                    "path": "/Shared Documents/Policies",
                    "recursive": False,
                    "max_items": 10,
                    "correlation_id": "local-example-001",
                },
            )
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
