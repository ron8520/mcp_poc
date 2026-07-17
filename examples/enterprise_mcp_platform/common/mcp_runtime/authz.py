from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_POLICY_PATH = Path(__file__).parents[2] / "policy" / "generated" / "tool_allowlist.json"
POLICY_PATH = Path(os.getenv("MCP_POLICY_PATH", str(DEFAULT_POLICY_PATH)))


@dataclass(frozen=True)
class Caller:
    subject: str
    client_id: str
    groups: frozenset[str]
    app_roles: frozenset[str]
    scopes: frozenset[str]


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    matched_role: str | None = None


def _split_env(name: str) -> frozenset[str]:
    values = os.getenv(name, "")
    return frozenset(value.strip() for value in values.split(",") if value.strip())


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise PermissionError(f"missing trusted caller claim: {name}")
    return value


def _required_split_env(name: str) -> frozenset[str]:
    values = _split_env(name)
    if not values:
        raise PermissionError(f"missing trusted caller claim: {name}")
    return values


def caller_from_environment() -> Caller:
    """Read trusted caller claims from the local adapter/runtime environment."""
    return Caller(
        subject=_required_env("MCP_SUBJECT"),
        client_id=_required_env("MCP_CLIENT_ID"),
        groups=_split_env("MCP_GROUPS"),
        app_roles=_required_split_env("MCP_APP_ROLES"),
        scopes=_required_split_env("MCP_SCOPES"),
    )


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def authorize_tool(
    caller: Caller,
    tool_name: str,
    site_id: str,
    change_ticket_id: str | None = None,
    resource_path: str | None = None,
    policy: dict[str, Any] | None = None,
) -> Decision:
    active_policy = policy or load_policy()
    normalized_site_id = site_id.strip()

    if "subjects" in active_policy and "tools" in active_policy:
        return _authorize_tool_policy(
            active_policy,
            caller,
            tool_name,
            normalized_site_id,
            change_ticket_id,
            resource_path,
        )

    for role_name, role in active_policy.get("roles", {}).items():
        if not _caller_matches_role(caller, role):
            continue

        if tool_name not in set(role.get("allowed_tools", [])):
            continue

        if normalized_site_id not in set(role.get("allowed_sites", [])):
            return Decision(False, "site_not_allowed", role_name)

        write_tools = set(role.get("write_tools", []))
        if tool_name in write_tools and role.get("requires_change_ticket"):
            if not change_ticket_id:
                return Decision(False, "change_ticket_required", role_name)

        return Decision(True, "allowed", role_name)

    return Decision(False, "no_matching_allow_rule")


def allowed_tools_for_caller(caller: Caller, policy: dict[str, Any] | None = None) -> list[str]:
    active_policy = policy or load_policy()
    if "subjects" not in active_policy or "tools" not in active_policy:
        allowed: set[str] = set()
        for role in active_policy.get("roles", {}).values():
            if _caller_matches_role(caller, role):
                allowed.update(role.get("allowed_tools", []))
        return sorted(allowed)

    allowed = []
    for tool_name, tool in active_policy.get("tools", {}).items():
        if tool_name == active_policy.get("discovery", {}).get("semantic_search", {}).get("tool_name"):
            continue
        if not tool.get("discovery", {}).get("searchable", False):
            continue
        if _caller_matches_any_subject(
            caller,
            tool.get("authorization", {}).get("allowed_subjects", []),
            active_policy,
        ):
            allowed.append(tool_name)
    return sorted(allowed)


def _authorize_tool_policy(
    policy: dict[str, Any],
    caller: Caller,
    tool_name: str,
    site_id: str,
    change_ticket_id: str | None,
    resource_path: str | None,
) -> Decision:
    tool = policy.get("tools", {}).get(tool_name)
    if not tool:
        return Decision(False, "unknown_tool")

    allowed_subjects = tool.get("authorization", {}).get("allowed_subjects", [])
    matched_subject = _first_matching_subject(caller, allowed_subjects, policy)
    if not matched_subject:
        return Decision(False, "no_matching_allow_rule")

    allowed_sites = tool.get("authorization", {}).get("allowed_sites", [])
    if allowed_sites and not _site_allowed(policy, allowed_sites, site_id):
        return Decision(False, "site_not_allowed", matched_subject)

    input_constraints = tool.get("input_constraints", {})
    if input_constraints.get("path_must_be_under_allowed_paths"):
        if not resource_path:
            return Decision(False, "path_required", matched_subject)
        if not _path_allowed(policy, allowed_sites, site_id, resource_path):
            return Decision(False, "path_not_allowed", matched_subject)

    if tool.get("write", False):
        controls = tool.get("write_controls", {})
        if controls.get("require_change_ticket") and not change_ticket_id:
            return Decision(False, "change_ticket_required", matched_subject)

    return Decision(True, "allowed", matched_subject)


def _caller_matches_role(caller: Caller, role: dict[str, Any]) -> bool:
    checks: list[bool] = []

    client_ids = set(role.get("client_ids", []))
    if client_ids:
        checks.append(caller.client_id in client_ids)

    groups = set(role.get("groups", []))
    if groups:
        checks.append(bool(caller.groups.intersection(groups)))

    app_roles = set(role.get("app_roles", []))
    if app_roles:
        checks.append(bool(caller.app_roles.intersection(app_roles)))

    return bool(checks) and all(checks)


def _caller_matches_any_subject(
    caller: Caller,
    subject_names: list[str],
    policy: dict[str, Any],
) -> bool:
    return _first_matching_subject(caller, subject_names, policy) is not None


def _first_matching_subject(
    caller: Caller,
    subject_names: list[str],
    policy: dict[str, Any],
) -> str | None:
    subjects = policy.get("subjects", {})
    for subject_name in subject_names:
        subject = subjects.get(subject_name)
        if subject and _caller_matches_subject(caller, subject):
            return subject_name
    return None


def _caller_matches_subject(caller: Caller, subject: dict[str, Any]) -> bool:
    entra = subject.get("entra", {})
    checks: list[bool] = []

    client_ids = set(entra.get("allowed_clients", []))
    if client_ids:
        checks.append(caller.client_id in client_ids)

    required_scopes = set(entra.get("required_scopes", []))
    if required_scopes:
        checks.append(required_scopes.issubset(caller.scopes))

    required_groups = set(entra.get("required_groups_any", []))
    if required_groups:
        checks.append(bool(caller.groups.intersection(required_groups)))

    required_roles = set(entra.get("required_roles_any", []))
    if required_roles:
        checks.append(bool(caller.app_roles.intersection(required_roles)))

    return bool(checks) and all(checks)


def _site_allowed(policy: dict[str, Any], allowed_site_refs: list[str], site_id: str) -> bool:
    sites = policy.get("approved_resources", {}).get("sharepoint_sites", {})
    for site_ref in allowed_site_refs:
        if site_ref == site_id:
            return True
        if sites.get(site_ref, {}).get("site_id") == site_id:
            return True
    return False


def _path_allowed(
    policy: dict[str, Any],
    allowed_site_refs: list[str],
    site_id: str,
    resource_path: str,
) -> bool:
    site = _matched_sharepoint_site(policy, allowed_site_refs, site_id)
    if not site:
        return False

    requested = _normalize_sharepoint_path(resource_path)
    for allowed_path in site.get("allowed_paths", []):
        allowed = _normalize_sharepoint_path(str(allowed_path))
        if requested == allowed or requested.startswith(f"{allowed}/"):
            return True
    return False


def _matched_sharepoint_site(
    policy: dict[str, Any],
    allowed_site_refs: list[str],
    site_id: str,
) -> dict[str, Any] | None:
    sites = policy.get("approved_resources", {}).get("sharepoint_sites", {})
    for site_ref in allowed_site_refs:
        site = sites.get(site_ref)
        if site and site.get("site_id") == site_id:
            return site
        if site_ref == site_id:
            return {"site_id": site_id, "allowed_paths": ["/"]}
    return None


def _normalize_sharepoint_path(path: str) -> str:
    normalized = "/" + path.strip().strip("/")
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized
