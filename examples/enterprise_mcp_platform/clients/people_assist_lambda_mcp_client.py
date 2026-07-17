from __future__ import annotations

import json
import os
import time
from urllib import parse
from urllib import request

_TOKEN_CACHE: dict[str, object] = {}
DEFAULT_MCP_AUDIENCE = "api://enterprise-mcp-nonprod"


def _mcp_audience() -> str:
    return os.getenv("ENTRA_MCP_AUDIENCE", DEFAULT_MCP_AUDIENCE).rstrip("/")


def _get_entra_app_token() -> str:
    cached_token = _TOKEN_CACHE.get("access_token")
    expires_at = float(_TOKEN_CACHE.get("expires_at", 0))
    if cached_token and time.time() < expires_at - 60:
        return str(cached_token)

    tenant_id = os.environ["ENTRA_TENANT_ID"]
    client_id = os.environ["ENTRA_CLIENT_ID"]
    client_secret = os.environ["ENTRA_CLIENT_SECRET"]
    scope = os.getenv("ENTRA_TOKEN_SCOPE", f"{_mcp_audience()}/.default")
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    token_request = request.Request(
        token_url,
        data=parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with request.urlopen(token_request, timeout=30) as response:
        token_response = json.loads(response.read().decode("utf-8"))

    _TOKEN_CACHE["access_token"] = token_response["access_token"]
    _TOKEN_CACHE["expires_at"] = time.time() + int(token_response.get("expires_in", 3600))
    return str(_TOKEN_CACHE["access_token"])


def lambda_handler(event: dict, context: object) -> dict:
    """People Assist Lambda client example. This is not AgentCore Gateway."""
    gateway_url = os.environ["ENTERPRISE_MCP_URL"]
    token = _get_entra_app_token()
    correlation_id = event.get("correlation_id", getattr(context, "aws_request_id", "unknown"))

    payload = {
        "jsonrpc": "2.0",
        "id": correlation_id,
        "method": "tools/call",
        "params": {
            "name": "sharepoint_get_file_text",
            "arguments": {
                "site_id": event["site_id"],
                "drive_id": event["drive_id"],
                "item_id": event["item_id"],
                "max_chars": event.get("max_chars", 8000),
                "correlation_id": correlation_id,
            },
        },
    }

    http_request = request.Request(
        gateway_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-correlation-id": correlation_id,
        },
        method="POST",
    )

    with request.urlopen(http_request, timeout=30) as response:
        body = response.read().decode("utf-8")

    return {
        "statusCode": 200,
        "correlation_id": correlation_id,
        "body": body,
    }
