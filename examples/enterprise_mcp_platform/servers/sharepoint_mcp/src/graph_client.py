from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from servers.sharepoint_mcp.src.graph_auth import GraphTokenProvider


GRAPH_API_ROOT = "https://graph.microsoft.com/v1.0"


def _dry_run_from_environment() -> bool:
    value = os.getenv("GRAPH_DRY_RUN")
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("GRAPH_DRY_RUN must be exactly true or false")


@dataclass
class SharePointGraphClient:
    dry_run: bool = field(default_factory=_dry_run_from_environment)
    token_provider: GraphTokenProvider | None = None

    def __post_init__(self) -> None:
        if not self.dry_run and self.token_provider is None:
            self.token_provider = GraphTokenProvider.from_environment()

    @property
    def user_assertion_header(self) -> str:
        if self.token_provider is None:
            return "x-mcp-user-assertion"
        return self.token_provider.config.user_assertion_header

    def list_site_content(
        self,
        site_id: str,
        path: str,
        recursive: bool,
        max_items: int,
        user_assertion: str | None = None,
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
        self._acquire_access_token(user_assertion)
        raise NotImplementedError("Wire Microsoft Graph client here")

    def get_file_text(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        max_chars: int,
        user_assertion: str | None = None,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "graph_method": "GET",
                "graph_path": f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/content",
                "text": "Example extracted text. Replace dry-run mode with Graph content extraction.",
                "truncated": False,
                "max_chars": max_chars,
            }
        self._acquire_access_token(user_assertion)
        raise NotImplementedError("Wire Microsoft Graph file download and text extraction here")

    def upload_file(
        self,
        site_id: str,
        file_path: str,
        content: str,
        user_assertion: str | None = None,
    ) -> dict[str, Any]:
        graph_path = (
            f"/sites/{quote(site_id, safe=',')}/drive/root:"
            f"/{quote(file_path, safe='/')}:/content"
        )
        if self.dry_run:
            return {
                "graph_method": "PUT",
                "graph_path": graph_path,
                "content_length": len(content.encode("utf-8")),
                "status": "dry_run",
            }

        request = Request(
            f"{GRAPH_API_ROOT}{graph_path}",
            data=content.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._acquire_access_token(user_assertion)}",
                "Content-Type": "text/plain; charset=utf-8",
            },
            method="PUT",
        )
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def _acquire_access_token(self, user_assertion: str | None) -> str:
        if self.token_provider is None:
            raise RuntimeError("Graph token provider is not configured")
        return self.token_provider.acquire_access_token(user_assertion)
