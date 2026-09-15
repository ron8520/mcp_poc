from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

import pymupdf

from servers.sharepoint_mcp.src.graph_auth import GraphTokenProvider
from servers.sharepoint_mcp.src.config import graph_dry_run_from_environment


GRAPH_API_ROOT = "https://graph.microsoft.com/v1.0"
GRAPH_REQUEST_TIMEOUT_SECONDS = 30
MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 250


class GraphClientError(RuntimeError):
    """Raised when a Graph response cannot be handled safely."""


@dataclass
class SharePointGraphClient:
    dry_run: bool = field(default_factory=graph_dry_run_from_environment)
    token_provider: GraphTokenProvider | None = None
    access_token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.dry_run and self.access_token is None and self.token_provider is None:
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
        graph_path = _site_children_path(site_id, path, max_items)
        if self.dry_run:
            return {
                "graph_method": "GET",
                "graph_path": graph_path,
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

        access_token = self._acquire_access_token(user_assertion)
        pending = deque([graph_path])
        items: list[dict[str, str]] = []

        while pending and len(items) < max_items:
            response = _graph_get_json(pending.popleft(), access_token)
            page_items = response.get("value")
            if not isinstance(page_items, list):
                raise GraphClientError(
                    "Microsoft Graph returned an invalid item collection"
                )

            child_paths: list[str] = []
            for item in page_items:
                safe_item = _safe_drive_item(item)
                items.append(safe_item)
                if recursive and safe_item["type"] == "folder":
                    child_paths.append(
                        _drive_item_children_path(
                            safe_item["drive_id"],
                            safe_item["item_id"],
                            max_items - len(items),
                        )
                    )
                if len(items) == max_items:
                    break

            next_link = response.get("@odata.nextLink")
            if next_link is not None:
                pending.appendleft(_validated_graph_url(next_link))
            pending.extend(child_paths)

        return {
            "graph_method": "GET",
            "graph_path": graph_path,
            "recursive": recursive,
            "max_items": max_items,
            "items": items,
        }

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
                "graph_path": f"/drives/{drive_id}/items/{item_id}",
                "text": "Example extracted text. Replace dry-run mode with Graph content extraction.",
                "truncated": False,
                "max_chars": max_chars,
            }

        metadata = _graph_get_json(
            f"/drives/{quote(drive_id, safe='')}/items/{quote(item_id, safe='')}",
            self._acquire_access_token(user_assertion),
        )
        parent_reference = metadata.get("parentReference")
        if (
            metadata.get("id") != item_id
            or not isinstance(parent_reference, dict)
            or parent_reference.get("driveId") != drive_id
            or parent_reference.get("siteId") != site_id
        ):
            raise GraphClientError(
                "The requested file does not belong to the supplied site"
            )
        if not isinstance(metadata.get("file"), dict):
            raise GraphClientError("The requested SharePoint item is not a file")

        name = metadata.get("name")
        size = metadata.get("size")
        download_url = metadata.get("@microsoft.graph.downloadUrl")
        if not isinstance(name, str) or not name:
            raise GraphClientError("Microsoft Graph returned invalid file metadata")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise GraphClientError(
                "Microsoft Graph returned invalid file size metadata"
            )
        if size > MAX_PDF_BYTES:
            raise GraphClientError(
                "The requested PDF exceeds the 25 MiB download limit"
            )
        if not isinstance(download_url, str) or not download_url:
            raise GraphClientError("Microsoft Graph did not return a file download URL")

        pdf_bytes = _download_file(download_url)
        text, truncated = _extract_pdf_text(pdf_bytes, max_chars)
        return {
            "name": name,
            "text": text,
            "truncated": truncated,
            "max_chars": max_chars,
        }

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
        with urlopen(request, timeout=GRAPH_REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)

    def _acquire_access_token(self, user_assertion: str | None) -> str:
        if self.access_token is not None:
            return self.access_token
        if self.token_provider is None:
            raise RuntimeError("Graph token provider is not configured")
        return self.token_provider.acquire_access_token(user_assertion)


def _site_children_path(site_id: str, path: str, max_items: int) -> str:
    encoded_site_id = quote(site_id, safe=",")
    if path == "/":
        base_path = f"/sites/{encoded_site_id}/drive/root/children"
    else:
        if not path.startswith("/") or any(
            part in {"", ".", ".."} for part in path[1:].split("/")
        ):
            raise ValueError(
                "path must be / or an absolute path without empty, . or .. segments"
            )
        base_path = (
            f"/sites/{encoded_site_id}/drive/root:"
            f"/{quote(path[1:], safe='/')}:/children"
        )
    return f"{base_path}?{urlencode({'$top': min(max_items, 200)})}"


def _drive_item_children_path(drive_id: str, item_id: str, remaining: int) -> str:
    top = min(max(remaining, 1), 200)
    return (
        f"/drives/{quote(drive_id, safe='')}/items/{quote(item_id, safe='')}/children"
        f"?{urlencode({'$top': top})}"
    )


def _safe_drive_item(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise GraphClientError("Microsoft Graph returned invalid item metadata")

    name = value.get("name")
    item_id = value.get("id")
    parent_reference = value.get("parentReference")
    if not isinstance(parent_reference, dict):
        raise GraphClientError("Microsoft Graph returned invalid item metadata")
    drive_id = parent_reference.get("driveId")
    if not all(isinstance(part, str) and part for part in (name, item_id, drive_id)):
        raise GraphClientError("Microsoft Graph returned invalid item metadata")

    if isinstance(value.get("folder"), dict):
        item_type = "folder"
    elif isinstance(value.get("file"), dict):
        item_type = "file"
    else:
        item_type = "other"

    return {
        "name": name,
        "type": item_type,
        "drive_id": drive_id,
        "item_id": item_id,
    }


def _validated_graph_url(value: object) -> str:
    if not isinstance(value, str) or not value.startswith(f"{GRAPH_API_ROOT}/"):
        raise GraphClientError("Microsoft Graph returned an invalid pagination URL")
    return value


def _graph_get_json(graph_path_or_url: str, access_token: str) -> dict[str, Any]:
    if graph_path_or_url.startswith("/"):
        url = f"{GRAPH_API_ROOT}{graph_path_or_url}"
    else:
        url = _validated_graph_url(graph_path_or_url)

    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=GRAPH_REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise GraphClientError(
            f"Microsoft Graph request failed with HTTP {exc.code}"
        ) from None
    except (OSError, URLError, json.JSONDecodeError):
        raise GraphClientError("Microsoft Graph request failed") from None

    if not isinstance(payload, dict):
        raise GraphClientError("Microsoft Graph returned an invalid JSON response")
    return payload


def _download_file(download_url: str) -> bytes:
    parsed = urlsplit(download_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise GraphClientError("Microsoft Graph returned an invalid file download URL")

    try:
        with urlopen(download_url, timeout=GRAPH_REQUEST_TIMEOUT_SECONDS) as response:
            content = response.read(MAX_PDF_BYTES + 1)
    except HTTPError as exc:
        raise GraphClientError(
            f"SharePoint file download failed with HTTP {exc.code}"
        ) from None
    except (OSError, URLError):
        raise GraphClientError("SharePoint file download failed") from None

    if len(content) > MAX_PDF_BYTES:
        raise GraphClientError("The requested PDF exceeds the 25 MiB download limit")
    return content


def _extract_pdf_text(pdf_bytes: bytes, max_chars: int) -> tuple[str, bool]:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise GraphClientError("The requested SharePoint file is not a PDF")

    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.page_count > MAX_PDF_PAGES:
                raise GraphClientError("The requested PDF exceeds the 250 page limit")
            text = ""
            truncated = False
            for page in document:
                page_text = page.get_text()
                if text and page_text:
                    page_text = f"\n{page_text}"
                remaining = max_chars - len(text)
                if len(page_text) > remaining:
                    text += page_text[:remaining]
                    truncated = True
                    break
                text += page_text
    except GraphClientError:
        raise
    except Exception:
        raise GraphClientError(
            "The requested SharePoint file is not a readable PDF"
        ) from None

    return text, truncated
