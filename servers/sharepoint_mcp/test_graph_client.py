from __future__ import annotations

import io
import json
import os
import unittest
from unittest.mock import patch

import pymupdf

from servers.sharepoint_mcp.src.graph_client import (
    MAX_PDF_BYTES,
    GraphClientError,
    SharePointGraphClient,
    _download_file,
    _extract_pdf_text,
)


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


def _json_response(value: object) -> FakeResponse:
    return FakeResponse(json.dumps(value).encode("utf-8"))


def _pdf_bytes(text: str, page_count: int = 1) -> bytes:
    with pymupdf.open() as document:
        for _ in range(page_count):
            page = document.new_page()
            page.insert_text((72, 72), text)
        return document.tobytes()


class SharePointGraphClientTest(unittest.TestCase):
    def test_dry_run_mode_accepts_only_exact_true_and_false(self) -> None:
        for value, expected in (("true", True), ("false", False)):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"GRAPH_DRY_RUN": value},
            ):
                self.assertIs(SharePointGraphClient().dry_run, expected)

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

    def test_dry_run_list_uses_agentcore_safe_graph_path(self) -> None:
        client = SharePointGraphClient(dry_run=True)

        result = client.list_site_content(
            "contoso.sharepoint.com,site-collection-guid,site-guid",
            "/Shared Documents/Policies",
            False,
            10,
        )

        self.assertEqual(
            result["graph_path"],
            "/sites/contoso.sharepoint.com,site-collection-guid,site-guid"
            "/drive/root:/Shared%20Documents/Policies:/children?%24top=10",
        )

    def test_list_rejects_ambiguous_path_without_repair(self) -> None:
        client = SharePointGraphClient(dry_run=True)

        for path in ("Policies", "/Policies/", "/Policies//Current", "/Policies/../HR"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "path must be"):
                    client.list_site_content("site-id", path, False, 10)

    def test_live_recursive_list_follows_graph_pagination_and_folder_children(
        self,
    ) -> None:
        client = SharePointGraphClient(
            dry_run=False,
            token_provider=FakeTokenProvider(),  # type: ignore[arg-type]
        )
        next_link = "https://graph.microsoft.com/v1.0/next-page"
        root_page = {
            "value": [
                {
                    "id": "folder-id",
                    "name": "Policies",
                    "folder": {"childCount": 1},
                    "parentReference": {"driveId": "drive-id"},
                }
            ],
            "@odata.nextLink": next_link,
        }
        second_page = {
            "value": [
                {
                    "id": "root-file-id",
                    "name": "root.pdf",
                    "file": {"mimeType": "application/pdf"},
                    "parentReference": {"driveId": "drive-id"},
                }
            ]
        }
        folder_page = {
            "value": [
                {
                    "id": "child-file-id",
                    "name": "child.pdf",
                    "file": {"mimeType": "application/pdf"},
                    "parentReference": {"driveId": "drive-id"},
                }
            ]
        }

        with patch(
            "servers.sharepoint_mcp.src.graph_client.urlopen",
            side_effect=[
                _json_response(root_page),
                _json_response(second_page),
                _json_response(folder_page),
            ],
        ) as open_url:
            result = client.list_site_content(
                "contoso.sharepoint.com,site-collection-guid,site-guid",
                "/",
                True,
                3,
                "gateway-assertion",
            )

        self.assertEqual(
            [item["name"] for item in result["items"]],
            ["Policies", "root.pdf", "child.pdf"],
        )
        requests = [call.args[0] for call in open_url.call_args_list]
        self.assertEqual(requests[1].full_url, next_link)
        self.assertIn("/drives/drive-id/items/folder-id/children", requests[2].full_url)
        for request in requests:
            self.assertEqual(request.get_header("Authorization"), "Bearer graph-token")

    def test_live_get_file_text_validates_site_and_downloads_without_graph_token(
        self,
    ) -> None:
        pdf = _pdf_bytes("AgentCore SharePoint PDF")
        metadata = {
            "id": "item-id",
            "name": "policy.pdf",
            "size": len(pdf),
            "file": {"mimeType": "application/pdf"},
            "parentReference": {
                "driveId": "drive-id",
                "siteId": "contoso.sharepoint.com,site-collection-guid,site-guid",
            },
            "@microsoft.graph.downloadUrl": "https://download.example/policy.pdf?token=short-lived",
        }
        client = SharePointGraphClient(
            dry_run=False,
            token_provider=FakeTokenProvider(),  # type: ignore[arg-type]
        )

        with patch(
            "servers.sharepoint_mcp.src.graph_client.urlopen",
            side_effect=[_json_response(metadata), FakeResponse(pdf)],
        ) as open_url:
            result = client.get_file_text(
                "contoso.sharepoint.com,site-collection-guid,site-guid",
                "drive-id",
                "item-id",
                12,
                "gateway-assertion",
            )

        metadata_request = open_url.call_args_list[0].args[0]
        download_request = open_url.call_args_list[1].args[0]
        self.assertEqual(
            metadata_request.get_header("Authorization"), "Bearer graph-token"
        )
        self.assertEqual(
            download_request,
            "https://download.example/policy.pdf?token=short-lived",
        )
        self.assertEqual(result["name"], "policy.pdf")
        self.assertEqual(len(result["text"]), 12)
        self.assertTrue(result["truncated"])

    def test_live_get_file_text_rejects_cross_site_item_before_download(self) -> None:
        metadata = {
            "id": "item-id",
            "name": "policy.pdf",
            "size": 100,
            "file": {"mimeType": "application/pdf"},
            "parentReference": {"driveId": "drive-id", "siteId": "different-site"},
            "@microsoft.graph.downloadUrl": "https://download.example/policy.pdf",
        }
        client = SharePointGraphClient(
            dry_run=False,
            token_provider=FakeTokenProvider(),  # type: ignore[arg-type]
        )

        with patch(
            "servers.sharepoint_mcp.src.graph_client.urlopen",
            return_value=_json_response(metadata),
        ) as open_url:
            with self.assertRaisesRegex(GraphClientError, "does not belong"):
                client.get_file_text(
                    "approved-site",
                    "drive-id",
                    "item-id",
                    100,
                    "gateway-assertion",
                )

        self.assertEqual(open_url.call_count, 1)

    def test_live_get_file_text_rejects_mismatched_drive_or_item_metadata(self) -> None:
        client = SharePointGraphClient(
            dry_run=False,
            token_provider=FakeTokenProvider(),  # type: ignore[arg-type]
        )
        for metadata in (
            {
                "id": "different-item",
                "name": "policy.pdf",
                "size": 100,
                "file": {"mimeType": "application/pdf"},
                "parentReference": {"driveId": "drive-id", "siteId": "approved-site"},
                "@microsoft.graph.downloadUrl": "https://download.example/policy.pdf",
            },
            {
                "id": "item-id",
                "name": "policy.pdf",
                "size": 100,
                "file": {"mimeType": "application/pdf"},
                "parentReference": {
                    "driveId": "different-drive",
                    "siteId": "approved-site",
                },
                "@microsoft.graph.downloadUrl": "https://download.example/policy.pdf",
            },
        ):
            with (
                self.subTest(metadata=metadata),
                patch(
                    "servers.sharepoint_mcp.src.graph_client.urlopen",
                    return_value=_json_response(metadata),
                ) as open_url,
                self.assertRaisesRegex(GraphClientError, "does not belong"),
            ):
                client.get_file_text(
                    "approved-site",
                    "drive-id",
                    "item-id",
                    100,
                    "gateway-assertion",
                )
            self.assertEqual(open_url.call_count, 1)

    def test_live_get_file_text_rejects_oversized_pdf_before_download(self) -> None:
        metadata = {
            "id": "item-id",
            "name": "large.pdf",
            "size": MAX_PDF_BYTES + 1,
            "file": {"mimeType": "application/pdf"},
            "parentReference": {"driveId": "drive-id", "siteId": "approved-site"},
            "@microsoft.graph.downloadUrl": "https://download.example/large.pdf",
        }
        client = SharePointGraphClient(
            dry_run=False,
            token_provider=FakeTokenProvider(),  # type: ignore[arg-type]
        )

        with patch(
            "servers.sharepoint_mcp.src.graph_client.urlopen",
            return_value=_json_response(metadata),
        ) as open_url:
            with self.assertRaisesRegex(GraphClientError, "25 MiB"):
                client.get_file_text(
                    "approved-site",
                    "drive-id",
                    "item-id",
                    100,
                    "gateway-assertion",
                )

        self.assertEqual(open_url.call_count, 1)

    def test_download_rejects_non_https_or_userinfo_urls(self) -> None:
        for download_url in (
            "http://download.example/policy.pdf",
            "https://user:password@download.example/policy.pdf",
        ):
            with (
                self.subTest(download_url=download_url),
                self.assertRaisesRegex(
                    GraphClientError,
                    "invalid file download URL",
                ),
            ):
                _download_file(download_url)

    def test_pdf_parser_hides_malformed_document_details(self) -> None:
        with self.assertRaisesRegex(GraphClientError, "not a readable PDF") as raised:
            _extract_pdf_text(b"%PDF-malformed", 100)

        self.assertNotIn("Failed to open", str(raised.exception))

    def test_pdf_parser_rejects_excessive_page_count(self) -> None:
        with self.assertRaisesRegex(GraphClientError, "250 page"):
            _extract_pdf_text(_pdf_bytes("page", page_count=251), 1000)

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
