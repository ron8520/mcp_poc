from __future__ import annotations

import asyncio
import os

from mcp import Client


async def main() -> None:
    mcp_url = os.getenv("MCP_URL", "http://localhost:8000/mcp")

    async with Client(
        mcp_url,
        mode="2026-07-28",
        read_timeout_seconds=120,
    ) as client:
        tools = await client.list_tools()
        print({"tools": [tool.name for tool in getattr(tools, "tools", [])]})

        result = await client.call_tool(
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
