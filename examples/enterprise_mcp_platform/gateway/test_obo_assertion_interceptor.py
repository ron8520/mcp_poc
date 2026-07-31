from __future__ import annotations

import unittest

from examples.enterprise_mcp_platform.gateway.obo_assertion_interceptor import (
    ASSERTION_HEADER,
    lambda_handler,
)


class OboAssertionInterceptorTest(unittest.TestCase):
    def test_initialize_passes_through(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {},
        }

        result = lambda_handler(
            {"mcp": {"gatewayRequest": {"body": body}}},
            object(),
        )

        self.assertEqual(
            result["mcp"]["transformedGatewayRequest"],
            {"body": body},
        )

    def test_malformed_tool_call_is_rejected(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "tools/call",
            "params": {},
        }

        with self.assertRaisesRegex(ValueError, "params.name"):
            lambda_handler(
                {"mcp": {"gatewayRequest": {"body": body}}},
                object(),
            )

    def test_delegated_lane_receives_validated_bearer_token(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "sharepoint-delegated___sharepoint_get_file_text",
                "arguments": {},
            },
        }
        result = lambda_handler(
            {
                "mcp": {
                    "gatewayRequest": {
                        "headers": {"Authorization": "Bearer header.payload.signature"},
                        "body": body,
                    }
                }
            },
            object(),
        )

        transformed = result["mcp"]["transformedGatewayRequest"]
        self.assertEqual(transformed["body"], body)
        self.assertEqual(
            transformed["headers"][ASSERTION_HEADER],
            "header.payload.signature",
        )

    def test_application_lane_never_receives_user_assertion(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "sharepoint-application___sharepoint_get_file_text",
                "arguments": {},
            },
        }
        result = lambda_handler(
            {
                "mcp": {
                    "gatewayRequest": {
                        "headers": {"Authorization": "Bearer app-token"},
                        "body": body,
                    }
                }
            },
            object(),
        )

        transformed = result["mcp"]["transformedGatewayRequest"]
        self.assertEqual(transformed, {"body": body})

    def test_delegated_lane_fails_closed_without_bearer_token(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "sharepoint-delegated___sharepoint_get_file_text",
                "arguments": {},
            },
        }
        result = lambda_handler(
            {
                "mcp": {
                    "gatewayRequest": {
                        "headers": {},
                        "body": body,
                    }
                }
            },
            object(),
        )

        response = result["mcp"]["transformedGatewayResponse"]
        self.assertEqual(response["statusCode"], 401)
        self.assertEqual(response["body"]["id"], 3)

    def test_bearer_token_whitespace_is_rejected_instead_of_trimmed(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "sharepoint-delegated___sharepoint_get_file_text",
                "arguments": {},
            },
        }
        result = lambda_handler(
            {
                "mcp": {
                    "gatewayRequest": {
                        "headers": {"Authorization": "Bearer token-with-space "},
                        "body": body,
                    }
                }
            },
            object(),
        )

        self.assertEqual(
            result["mcp"]["transformedGatewayResponse"]["statusCode"],
            401,
        )


if __name__ == "__main__":
    unittest.main()
