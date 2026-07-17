from __future__ import annotations

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(host="0.0.0.0", stateless_http=True)


@mcp.tool()
def crm_server_status() -> dict[str, str]:
    """Return server metadata. Business CRM tools are intentionally not enabled."""
    return {
        "server": "crm_mcp",
        "status": "placeholder",
        "business_tools_enabled": "false",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
