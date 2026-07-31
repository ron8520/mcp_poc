from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import Context, MCPServer

from common.mcp_runtime.audit import audit
from common.mcp_runtime.validation import (
    require_relative_path,
    require_safe_id,
    require_text,
)
from servers.sharepoint_mcp.src.graph_auth import user_assertion_from_context
from servers.sharepoint_mcp.src.graph_client import SharePointGraphClient


mcp = MCPServer("sharepoint-mcp")
graph = SharePointGraphClient()


@mcp.tool()
def sharepoint_list_site_content(
    site_id: str,
    correlation_id: str,
    ctx: Context,
    path: str = "/",
    recursive: bool = False,
    max_items: int = 50,
) -> dict[str, Any]:
    """List metadata for approved SharePoint site content."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_correlation_id = require_safe_id("correlation_id", correlation_id)
    safe_path = require_text("path", path)
    if max_items < 1 or max_items > 200:
        raise ValueError("max_items must be between 1 and 200")

    result = graph.list_site_content(
        safe_site_id,
        safe_path,
        recursive,
        max_items,
        user_assertion_from_context(ctx, graph.user_assertion_header),
    )
    audit(
        "tool.sharepoint_list_site_content",
        safe_correlation_id,
        "success",
        site_id=safe_site_id,
        recursive=recursive,
        max_items=max_items,
    )
    return {"status": "ok", "site_id": safe_site_id, "result": result}


@mcp.tool()
def sharepoint_get_file_text(
    site_id: str,
    drive_id: str,
    item_id: str,
    correlation_id: str,
    ctx: Context,
    max_chars: int = 8000,
) -> dict[str, Any]:
    """Read text from one approved SharePoint file."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_drive_id = require_safe_id("drive_id", drive_id)
    safe_item_id = require_safe_id("item_id", item_id)
    safe_correlation_id = require_safe_id("correlation_id", correlation_id)
    if max_chars < 1 or max_chars > 50000:
        raise ValueError("max_chars must be between 1 and 50000")

    result = graph.get_file_text(
        safe_site_id,
        safe_drive_id,
        safe_item_id,
        max_chars,
        user_assertion_from_context(ctx, graph.user_assertion_header),
    )
    audit(
        "tool.sharepoint_get_file_text",
        safe_correlation_id,
        "success",
        site_id=safe_site_id,
        max_chars=max_chars,
    )
    return {"status": "ok", "site_id": safe_site_id, "result": result}


@mcp.tool()
def sharepoint_upload_file(
    site_id: str,
    file_path: str,
    content: str,
    ctx: Context,
) -> dict[str, Any]:
    """Upload UTF-8 text content to the site's default document library."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_file_path = require_relative_path("file_path", file_path)
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    result = graph.upload_file(
        safe_site_id,
        safe_file_path,
        content,
        user_assertion_from_context(ctx, graph.user_assertion_header),
    )
    status = "dry_run" if graph.dry_run else "uploaded"
    return {"status": status, "site_id": safe_site_id, "result": result}


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        stateless_http=True,
    )
