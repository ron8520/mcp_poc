from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SharePointGraphClient:
    dry_run: bool = os.getenv("GRAPH_DRY_RUN", "true").lower() == "true"

    def list_site_content(
        self,
        site_id: str,
        path: str,
        recursive: bool,
        max_items: int,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "graph_method": "GET",
                "graph_path": f"/sites/{site_id}/drive/root:{path}:/children",
                "recursive": recursive,
                "max_items": max_items,
                "items": [
                    {
                        "name": "policy.md",
                        "type": "file",
                        "drive_id": "drive-id",
                        "item_id": "item-id",
                    }
                ],
            }
        raise NotImplementedError("Wire Microsoft Graph client here")

    def get_file_text(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        max_chars: int,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "graph_method": "GET",
                "graph_path": f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/content",
                "text": "Example extracted text. Replace dry-run mode with Graph content extraction.",
                "truncated": False,
                "max_chars": max_chars,
            }
        raise NotImplementedError("Wire Microsoft Graph file download and text extraction here")

    def insert_site_page_content(
        self,
        site_id: str,
        page_title: str,
        markdown_content: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "graph_method": "POST",
                "graph_path": f"/sites/{site_id}/pages",
                "page_title": page_title,
                "idempotency_key": idempotency_key,
                "status": "dry_run_created",
            }
        raise NotImplementedError("Wire Microsoft Graph page create API here")

    def update_file_content(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        expected_etag: str,
        content: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "graph_method": "PUT",
                "graph_path": f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/content",
                "expected_etag": expected_etag,
                "idempotency_key": idempotency_key,
                "content_length": len(content),
                "status": "dry_run_updated",
            }
        raise NotImplementedError("Wire Microsoft Graph upload session or content API here")
