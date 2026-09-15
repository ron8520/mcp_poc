from __future__ import annotations

import os


def graph_dry_run_from_environment() -> bool:
    value = os.getenv("GRAPH_DRY_RUN")
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("GRAPH_DRY_RUN must be exactly true or false")
