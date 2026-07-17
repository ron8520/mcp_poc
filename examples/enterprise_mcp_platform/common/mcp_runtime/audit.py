from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def audit(event_name: str, correlation_id: str, result: str, **metadata: Any) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        "correlation_id": correlation_id,
        "result": result,
        **metadata,
    }
    print(json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)
