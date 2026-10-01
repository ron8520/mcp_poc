from __future__ import annotations

import httpx

from servers.crm_mcp.src.auth import CRMConfig


def update_case_summary(
    config: CRMConfig,
    case_id: str,
    summary: str,
    token: str,
) -> None:
    # Do not retry writes: a timeout can follow a committed Dataverse update.
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.patch(
            f"{config.base_url}/api/data/v9.2/incidents({case_id})",
            headers={
                "Authorization": f"Bearer {token}",
                "If-Match": "*",
                "OData-Version": "4.0",
                "OData-MaxVersion": "4.0",
                "Prefer": "return=minimal",
            },
            json={config.summary_field: summary},
        )

    if response.status_code != 204:
        # Downstream bodies may contain record data; keep them out of MCP errors.
        raise RuntimeError(f"CRM update failed with HTTP {response.status_code}")
