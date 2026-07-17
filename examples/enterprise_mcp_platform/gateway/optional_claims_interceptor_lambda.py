from __future__ import annotations


def lambda_handler(event: dict, context: object) -> dict:
    """Optional Gateway interceptor Lambda. This is not the Gateway itself."""
    request_context = event.get("requestContext", {})
    identity = request_context.get("identity", {})
    request_id = request_context.get("requestId", getattr(context, "aws_request_id", "unknown"))

    subject = _safe_header(identity.get("subject") or identity.get("userId") or "unknown")
    client_id = _safe_header(identity.get("clientId") or "unknown")
    groups = _safe_header(",".join(identity.get("groups", [])))
    app_roles = _safe_header(",".join(identity.get("roles", [])))

    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": {
                    "x-mcp-subject": subject,
                    "x-mcp-client-id": client_id,
                    "x-mcp-groups": groups,
                    "x-mcp-app-roles": app_roles,
                    "x-correlation-id": request_id,
                },
                "body": event["mcp"]["gatewayRequest"]["body"],
            }
        },
    }


def _safe_header(value: object) -> str:
    text = str(value)
    return "".join(char for char in text if 32 <= ord(char) <= 126)[:1024]
