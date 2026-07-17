from __future__ import annotations

import json
import os
import sys
from urllib import request


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def main() -> None:
    gateway_url = _required_env("ENTERPRISE_MCP_URL")
    token = _required_env("ENTRA_ACCESS_TOKEN")
    query = os.getenv("AGENTCORE_TOOL_SEARCH_QUERY", "find SharePoint files")
    correlation_id = os.getenv("CORRELATION_ID", "gateway-search-example-001")

    payload = {
        "jsonrpc": "2.0",
        "id": correlation_id,
        "method": "tools/call",
        "params": {
            "name": "x_amz_bedrock_agentcore_search",
            "arguments": {
                "query": query,
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
        print(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
