from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer


mcp = MCPServer("internal-software-mcp")


@mcp.tool()
def internal_software_server_status() -> dict[str, str]:
    """Return server metadata. Business internal tools are not enabled."""
    return {
        "server": "internal_software_mcp",
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
