#!/usr/bin/env python3
import os
import socket
import sys


def main() -> int:
    host = os.environ.get("MCP_HEALTH_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8000"))
    timeout_seconds = float(os.environ.get("MCP_HEALTH_TIMEOUT_SECONDS", "2"))

    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return 0
    except OSError as exc:
        print(f"healthcheck failed: {host}:{port} is not reachable: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
