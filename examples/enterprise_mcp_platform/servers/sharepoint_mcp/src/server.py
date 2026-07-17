from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from common.mcp_runtime.audit import audit
from common.mcp_runtime.authz import authorize_tool, caller_from_environment
from common.mcp_runtime.validation import (
    require_audit_reason,
    require_change_ticket,
    require_safe_id,
    require_text,
)
from servers.sharepoint_mcp.src.graph_client import SharePointGraphClient


mcp = FastMCP(host="0.0.0.0", stateless_http=True)
graph = SharePointGraphClient()


def _authorize(
    tool_name: str,
    site_id: str,
    correlation_id: str,
    change_ticket_id: str | None = None,
    resource_path: str | None = None,
) -> str:
    caller = caller_from_environment()
    decision = authorize_tool(
        caller,
        tool_name,
        site_id,
        change_ticket_id,
        resource_path=resource_path,
    )
    audit(
        "authz.tool_decision",
        correlation_id,
        "allow" if decision.allowed else "deny",
        tool_name=tool_name,
        site_id=site_id,
        subject=caller.subject,
        client_id=caller.client_id,
        matched_role=decision.matched_role,
        reason=decision.reason,
    )
    if not decision.allowed:
        raise PermissionError(decision.reason)
    return decision.matched_role or "unknown"


@mcp.tool()
def sharepoint_list_site_content(
    site_id: str,
    correlation_id: str,
    path: str = "/",
    recursive: bool = False,
    max_items: int = 50,
) -> dict[str, Any]:
    """List metadata for approved SharePoint site content."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_correlation_id = require_safe_id("correlation_id", correlation_id)
    safe_path = require_text("path", path, 300)
    if max_items < 1 or max_items > 200:
        raise ValueError("max_items must be between 1 and 200")

    matched_role = _authorize(
        "sharepoint_list_site_content",
        safe_site_id,
        safe_correlation_id,
        resource_path=safe_path,
    )
    result = graph.list_site_content(safe_site_id, safe_path, recursive, max_items)
    audit(
        "tool.sharepoint_list_site_content",
        safe_correlation_id,
        "success",
        site_id=safe_site_id,
        matched_role=matched_role,
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
    max_chars: int = 8000,
) -> dict[str, Any]:
    """Read text from one approved SharePoint file."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_drive_id = require_safe_id("drive_id", drive_id)
    safe_item_id = require_safe_id("item_id", item_id)
    safe_correlation_id = require_safe_id("correlation_id", correlation_id)
    if max_chars < 1 or max_chars > 50000:
        raise ValueError("max_chars must be between 1 and 50000")

    matched_role = _authorize(
        "sharepoint_get_file_text",
        safe_site_id,
        safe_correlation_id,
    )
    result = graph.get_file_text(safe_site_id, safe_drive_id, safe_item_id, max_chars)
    audit(
        "tool.sharepoint_get_file_text",
        safe_correlation_id,
        "success",
        site_id=safe_site_id,
        matched_role=matched_role,
        max_chars=max_chars,
    )
    return {"status": "ok", "site_id": safe_site_id, "result": result}


@mcp.tool()
def sharepoint_insert_site_page_content(
    site_id: str,
    page_title: str,
    markdown_content: str,
    change_ticket_id: str,
    idempotency_key: str,
    audit_reason: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Insert content into an approved SharePoint site page."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_title = require_text("page_title", page_title, 120)
    safe_content = require_text("markdown_content", markdown_content, 50000)
    safe_ticket = require_change_ticket(change_ticket_id)
    safe_idempotency_key = require_safe_id("idempotency_key", idempotency_key, 220)
    safe_audit_reason = require_audit_reason(audit_reason)
    safe_correlation_id = require_safe_id("correlation_id", correlation_id)

    matched_role = _authorize(
        "sharepoint_insert_site_page_content",
        safe_site_id,
        safe_correlation_id,
        safe_ticket,
    )
    result = graph.insert_site_page_content(
        safe_site_id,
        safe_title,
        safe_content,
        safe_idempotency_key,
    )
    audit(
        "tool.sharepoint_insert_site_page_content",
        safe_correlation_id,
        "success",
        site_id=safe_site_id,
        matched_role=matched_role,
        change_ticket_id=safe_ticket,
        audit_reason=safe_audit_reason,
        content_length=len(safe_content),
    )
    return {"status": "ok", "site_id": safe_site_id, "result": result}


@mcp.tool()
def sharepoint_update_file_content(
    site_id: str,
    drive_id: str,
    item_id: str,
    expected_etag: str,
    content: str,
    change_ticket_id: str,
    idempotency_key: str,
    audit_reason: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Modify one approved SharePoint file with optimistic concurrency."""
    safe_site_id = require_safe_id("site_id", site_id)
    safe_drive_id = require_safe_id("drive_id", drive_id)
    safe_item_id = require_safe_id("item_id", item_id)
    safe_etag = require_text("expected_etag", expected_etag, 160)
    safe_content = require_text("content", content, 50000)
    safe_ticket = require_change_ticket(change_ticket_id)
    safe_idempotency_key = require_safe_id("idempotency_key", idempotency_key, 220)
    safe_audit_reason = require_audit_reason(audit_reason)
    safe_correlation_id = require_safe_id("correlation_id", correlation_id)

    matched_role = _authorize(
        "sharepoint_update_file_content",
        safe_site_id,
        safe_correlation_id,
        safe_ticket,
    )
    result = graph.update_file_content(
        safe_site_id,
        safe_drive_id,
        safe_item_id,
        safe_etag,
        safe_content,
        safe_idempotency_key,
    )
    audit(
        "tool.sharepoint_update_file_content",
        safe_correlation_id,
        "success",
        site_id=safe_site_id,
        matched_role=matched_role,
        change_ticket_id=safe_ticket,
        audit_reason=safe_audit_reason,
        content_length=len(safe_content),
    )
    return {"status": "ok", "site_id": safe_site_id, "result": result}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
