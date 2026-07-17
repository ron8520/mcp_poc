from __future__ import annotations

import re


def require_safe_id(name: str, value: str, max_length: int = 160) -> str:
    text = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]{1,159}", text):
        raise ValueError(f"{name} must be a safe identifier")
    if len(text) > max_length:
        raise ValueError(f"{name} must be <= {max_length} characters")
    return text


def require_text(name: str, value: str, max_length: int) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{name} is required")
    if len(text) > max_length:
        raise ValueError(f"{name} must be <= {max_length} characters")
    return text


def require_change_ticket(value: str) -> str:
    text = value.strip()
    if not re.fullmatch(r"(CHG|RFC|ADO)-[A-Za-z0-9-]{3,64}", text):
        raise ValueError("change_ticket_id must reference an approved change")
    return text


def require_audit_reason(value: str) -> str:
    return require_text("audit_reason", value, 500)
