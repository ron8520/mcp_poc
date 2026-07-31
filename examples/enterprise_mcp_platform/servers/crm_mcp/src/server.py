from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer


mcp = MCPServer("crm-mcp")


@mcp.tool()
def crm_server_status() -> dict[str, str]:
    """Return server metadata. Business CRM tools are intentionally not enabled."""
    return {
        "server": "crm_mcp",
        "status": "placeholder",
        "business_tools_enabled": "false",
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        stateless_http=True,
    )
