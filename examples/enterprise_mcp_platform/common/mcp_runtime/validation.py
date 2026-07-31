from __future__ import annotations

import re


def require_safe_id(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:,/@-]*", value):
        raise ValueError(f"{name} must be a safe identifier")
    return value


def require_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} is required")
    return value


def require_relative_path(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value or value.startswith("/"):
        raise ValueError(f"{name} must be a non-empty relative path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"{name} contains an invalid path segment")
    return value
