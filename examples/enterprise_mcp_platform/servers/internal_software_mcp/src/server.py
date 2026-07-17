from __future__ import annotations

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(host="0.0.0.0", stateless_http=True)


@mcp.tool()
def internal_software_server_status() -> dict[str, str]:
    """Return server metadata. Business internal tools are not enabled."""
    return {
        "server": "internal_software_mcp",
        "status": "placeholder",
        "business_tools_enabled": "false",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
