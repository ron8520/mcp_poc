from __future__ import annotations

from typing import Any


DELEGATED_TARGET_PREFIX = "sharepoint-delegated___"
ASSERTION_HEADER = "x-mcp-user-assertion"
MAX_ASSERTION_LENGTH = 4096


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Inject the validated caller token only into delegated SharePoint calls."""
    gateway_request = event.get("mcp", {}).get("gatewayRequest", {})
    body = gateway_request.get("body")

    if not _is_delegated_lane_call(body):
        return _pass_through(body)

    bearer_token = _bearer_token(gateway_request.get("headers", {}))
    if bearer_token is None:
        return _authentication_error(body)

    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": {
                    ASSERTION_HEADER: bearer_token,
                },
                "body": body,
            }
        },
    }


def _is_delegated_lane_call(body: object) -> bool:
    if not isinstance(body, dict):
        raise ValueError("Gateway request body must be a JSON-RPC object")
    if body.get("method") != "tools/call":
        return False

    params = body.get("params")
    if not isinstance(params, dict):
        raise ValueError("tools/call params must be an object")

    tool_name = params.get("name")
    if not isinstance(tool_name, str) or not tool_name:
        raise ValueError("tools/call params.name must be a non-empty string")
    return tool_name.startswith(DELEGATED_TARGET_PREFIX)


def _bearer_token(headers: object) -> str | None:
    if not isinstance(headers, dict):
        return None

    authorization = next(
        (
            value
            for name, value in headers.items()
            if isinstance(name, str) and name.lower() == "authorization"
        ),
        None,
    )
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ")
    if not token or len(token) > MAX_ASSERTION_LENGTH:
        return None
    if any(ord(char) < 33 or ord(char) > 126 for char in token):
        return None
    return token


def _pass_through(body: object) -> dict[str, Any]:
    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "body": body,
            }
        },
    }


def _authentication_error(body: object) -> dict[str, Any]:
    request_id = body.get("id") if isinstance(body, dict) else None
    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayResponse": {
                "statusCode": 401,
                "body": {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32001,
                        "message": "Delegated user assertion is required",
                    },
                },
            }
        },
    }
