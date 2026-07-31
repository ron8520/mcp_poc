from __future__ import annotations

import io
import json
import os
import unittest
from unittest.mock import patch

from servers.sharepoint_mcp.src.graph_client import SharePointGraphClient


class FakeTokenProvider:
    def acquire_access_token(self, user_assertion: str | None = None) -> str:
        if user_assertion != "gateway-assertion":
            raise AssertionError("unexpected user assertion")
        return "graph-token"


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class SharePointGraphClientTest(unittest.TestCase):
    def test_dry_run_mode_must_be_explicit(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "exactly true or false"):
                SharePointGraphClient()

    def test_invalid_dry_run_value_fails_during_client_creation(self) -> None:
        with patch.dict(os.environ, {"GRAPH_DRY_RUN": "tru"}):
            with self.assertRaisesRegex(ValueError, "exactly true or false"):
                SharePointGraphClient()

    def test_dry_run_describes_upload_without_returning_content(self) -> None:
        client = SharePointGraphClient(dry_run=True)

        result = client.upload_file(
            "contoso.sharepoint.com,site-collection-guid,site-guid",
            "Folder A/file.txt",
            "hello",
        )

        self.assertEqual(result["graph_method"], "PUT")
        self.assertEqual(
            result["graph_path"],
            "/sites/contoso.sharepoint.com,site-collection-guid,site-guid"
            "/drive/root:/Folder%20A/file.txt:/content",
        )
        self.assertEqual(result["status"], "dry_run")
        self.assertNotIn("content", result)

    def test_live_upload_puts_utf8_content_to_default_document_library(self) -> None:
        response_body = {"id": "item-id", "name": "file.txt", "size": 6}
        client = SharePointGraphClient(
            dry_run=False,
            token_provider=FakeTokenProvider(),  # type: ignore[arg-type]
        )

        with patch(
            "servers.sharepoint_mcp.src.graph_client.urlopen",
            return_value=FakeResponse(json.dumps(response_body).encode("utf-8")),
        ) as open_url:
            result = client.upload_file(
                "contoso.sharepoint.com,site-collection-guid,site-guid",
                "Folder A/file.txt",
                "héllo",
                "gateway-assertion",
            )

        request = open_url.call_args.args[0]
        self.assertEqual(request.get_method(), "PUT")
        self.assertEqual(
            request.full_url,
            "https://graph.microsoft.com/v1.0/sites/"
            "contoso.sharepoint.com,site-collection-guid,site-guid"
            "/drive/root:/Folder%20A/file.txt:/content",
        )
        self.assertEqual(request.data, "héllo".encode("utf-8"))
        self.assertEqual(request.get_header("Authorization"), "Bearer graph-token")
        self.assertEqual(
            request.get_header("Content-type"),
            "text/plain; charset=utf-8",
        )
        self.assertEqual(open_url.call_args.kwargs, {"timeout": 30})
        self.assertEqual(result, response_body)


if __name__ == "__main__":
    unittest.main()
