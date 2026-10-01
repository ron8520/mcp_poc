import os
import re
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.tools import Tool
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict, Field

from servers.sharepoint_mcp.src import app_auth, auth, graph
from servers.sharepoint_mcp.src.audit import audit


mode = os.environ.get("GRAPH_AUTH_MODE")
if mode not in {"obo", "client_credentials", "agentcore_m2m"}:
    raise ValueError("GRAPH_AUTH_MODE must be agentcore_m2m, obo, or client_credentials")
config = app_auth.Config.from_environment() if mode == "agentcore_m2m" else auth.Config.from_environment()


def access_token(ctx: Context, site_id: str, tool_name: str) -> str:
    if mode == "agentcore_m2m":
        provider_arn = app_auth.authorize(config, ctx.headers, site_id, tool_name)
        return app_auth.access_token(config, provider_arn)
    return auth.access_token(config, ctx.headers)


def require_id(name: str, value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:,/@-]*", value):
        raise ValueError(f"{name} must be a safe identifier")


def require_path(name: str, value: str, *, absolute: bool = False) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty path")
    if absolute and value == "/":
        return
    if value.startswith("/") != absolute:
        raise ValueError(f"{name} must be {'absolute' if absolute else 'relative'}")
    segments = value[1:].split("/") if absolute else value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{name} contains an invalid path segment")


def sharepoint_list_site_content(
    site_id: str, correlation_id: str, ctx: Context,
    path: str = "/", recursive: bool = False, max_items: int = 50,
) -> dict[str, Any]:
    """List metadata from the site's default document library."""
    require_id("site_id", site_id)
    require_id("correlation_id", correlation_id)
    require_path("path", path, absolute=True)
    if type(recursive) is not bool or type(max_items) is not int or not 1 <= max_items <= 200:
        raise ValueError("recursive must be boolean; max_items must be an integer between 1 and 200")
    token = access_token(ctx, site_id, "sharepoint_list_site_content")
    result = graph.list_site_content(token, site_id, path, recursive, max_items)
    audit("tool.sharepoint_list_site_content", correlation_id, "success",
          site_id=site_id, recursive=recursive, max_items=max_items)
    return {"status": "ok", "site_id": site_id, "result": result}


def sharepoint_get_file_text(
    site_id: str, drive_id: str, item_id: str, correlation_id: str,
    ctx: Context, max_chars: int = 8000,
) -> dict[str, Any]:
    """Extract bounded text from one SharePoint PDF belonging to the supplied site."""
    for name, value in (("site_id", site_id), ("drive_id", drive_id),
                        ("item_id", item_id), ("correlation_id", correlation_id)):
        require_id(name, value)
    if type(max_chars) is not int or not 1 <= max_chars <= 50000:
        raise ValueError("max_chars must be an integer between 1 and 50000")
    token = access_token(ctx, site_id, "sharepoint_get_file_text")
    result = graph.get_file_text(token, site_id, drive_id, item_id, max_chars)
    audit("tool.sharepoint_get_file_text", correlation_id, "success", site_id=site_id, max_chars=max_chars)
    return {"status": "ok", "site_id": site_id, "result": result}


def sharepoint_upload_file(site_id: str, file_path: str, content: str, ctx: Context) -> dict[str, Any]:
    """Create or replace one UTF-8 text file in the site's default document library."""
    require_id("site_id", site_id)
    require_path("file_path", file_path)
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    token = access_token(ctx, site_id, "sharepoint_upload_file")
    result = graph.upload_file(token, site_id, file_path, content)
    return {"status": "uploaded", "site_id": site_id, "result": result}


class Arguments(ArgModelBase):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class ListArguments(Arguments):
    site_id: str
    correlation_id: str
    path: str = "/"
    recursive: bool = False
    max_items: int = Field(default=50, ge=1, le=200)


class ReadArguments(Arguments):
    site_id: str
    drive_id: str
    item_id: str
    correlation_id: str
    max_chars: int = Field(default=8000, ge=1, le=50000)


class UploadArguments(Arguments):
    site_id: str
    file_path: str
    content: str


tools = []
for function, arguments in ((sharepoint_list_site_content, ListArguments),
                            (sharepoint_get_file_text, ReadArguments),
                            (sharepoint_upload_file, UploadArguments)):
    # The SDK otherwise ignores unknown fields and uses permissive argument models.
    tool = Tool.from_function(function)
    tool.fn_metadata.arg_model = arguments
    tool.parameters = arguments.model_json_schema()
    tools.append(tool)
mcp = MCPServer("sharepoint-mcp", tools=tools)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")), stateless_http=True)
