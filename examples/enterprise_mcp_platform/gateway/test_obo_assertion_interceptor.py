from __future__ import annotations

import unittest

from gateway.obo_assertion_interceptor import (
    ASSERTION_HEADER,
    CALLER_ASSERTION_HEADER,
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

    def test_application_lane_receives_caller_assertion_and_overrides_client_header(
        self,
    ) -> None:
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
                        "headers": {
                            "Authorization": "Bearer app-token",
                            CALLER_ASSERTION_HEADER: "client-supplied-token",
                        },
                        "body": body,
                    }
                }
            },
            object(),
        )

        transformed = result["mcp"]["transformedGatewayRequest"]
        self.assertEqual(transformed["body"], body)
        self.assertEqual(
            transformed["headers"][CALLER_ASSERTION_HEADER],
            "app-token",
        )
        self.assertNotIn(ASSERTION_HEADER, transformed["headers"])

    def test_application_lane_fails_closed_without_bearer_token(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "sharepoint-application___sharepoint_upload_file",
                "arguments": {},
            },
        }

        result = lambda_handler(
            {"mcp": {"gatewayRequest": {"headers": {}, "body": body}}},
            object(),
        )

        response = result["mcp"]["transformedGatewayResponse"]
        self.assertEqual(response["statusCode"], 401)
        self.assertEqual(response["body"]["id"], 5)
        self.assertEqual(
            response["body"]["error"]["message"],
            "Application caller assertion is required",
        )

    def test_unknown_application_action_does_not_receive_sensitive_header(self) -> None:
        body = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "sharepoint-application___unknown_tool",
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

        self.assertEqual(
            result["mcp"]["transformedGatewayRequest"],
            {"body": body},
        )

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
