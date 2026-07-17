from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
DEFAULT_POLICY = ROOT / "tool_allowlist.yaml"
DEFAULT_SCHEMA = ROOT / "tool_allowlist.schema.json"
DEFAULT_GENERATED = ROOT / "generated" / "tool_allowlist.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Enterprise MCP policy YAML.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--generated", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated JSON artifact is not up to date.",
    )
    args = parser.parse_args()

    policy = load_yaml(args.policy)
    schema = load_json(args.schema)
    validate_schema(policy, schema)
    validate_references(policy)
    run_policy_tests(policy)

    rendered = render_json(policy)
    if args.check:
        existing = args.generated.read_text(encoding="utf-8")
        if existing != rendered:
            print(f"{args.generated} is not up to date", file=sys.stderr)
            return 1
    else:
        args.generated.parent.mkdir(parents=True, exist_ok=True)
        args.generated.write_text(rendered, encoding="utf-8")

    print(f"policy ok: {args.policy}")
    return 0


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def validate_schema(policy: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(policy), key=lambda error: list(error.path))
    if errors:
        for error in errors:
            path = ".".join(str(part) for part in error.path) or "<root>"
            print(f"schema error at {path}: {error.message}", file=sys.stderr)
        raise SystemExit(1)


def validate_references(policy: dict[str, Any]) -> None:
    subjects = set(policy["subjects"])
    tools = policy["tools"]
    sites = set(policy["approved_resources"]["sharepoint_sites"])

    search = policy["discovery"]["semantic_search"]
    require_known_subjects(search["allowed_subjects"], subjects, "discovery.semantic_search")
    require_known_subjects(search.get("denied_subjects", []), subjects, "discovery.semantic_search")

    if search["tool_name"] not in tools:
        raise ValueError(f"discovery semantic tool {search['tool_name']} is not listed in tools")

    for tool_name, tool in tools.items():
        location = f"tools.{tool_name}"
        require_known_subjects(tool["authorization"]["allowed_subjects"], subjects, location)
        for site_ref in tool["authorization"].get("allowed_sites", []):
            if site_ref not in sites:
                raise ValueError(f"{location} references unknown SharePoint site {site_ref}")

        required_inputs = set(tool.get("input_constraints", {}).get("required", []))
        controls = tool.get("write_controls", {})
        if controls.get("require_change_ticket") and "change_ticket_id" not in required_inputs:
            raise ValueError(f"{location} requires change_ticket_id in input_constraints.required")
        if controls.get("require_idempotency_key") and "idempotency_key" not in required_inputs:
            raise ValueError(f"{location} requires idempotency_key in input_constraints.required")
        if controls.get("require_expected_etag") and "expected_etag" not in required_inputs:
            raise ValueError(f"{location} requires expected_etag in input_constraints.required")
        if controls.get("require_expected_row_version") and "expected_row_version" not in required_inputs:
            raise ValueError(f"{location} requires expected_row_version in input_constraints.required")
        if controls.get("require_audit_reason") and "audit_reason" not in required_inputs:
            raise ValueError(f"{location} requires audit_reason in input_constraints.required")

    for test in policy["test_cases"]:
        subject_ref = test["caller"]["subject_ref"]
        if subject_ref not in subjects:
            raise ValueError(f"test {test['name']} references unknown subject {subject_ref}")
        tool_name = test.get("tool")
        if tool_name and tool_name not in tools:
            raise ValueError(f"test {test['name']} references unknown tool {tool_name}")


def require_known_subjects(subject_refs: list[str], subjects: set[str], location: str) -> None:
    for subject_ref in subject_refs:
        if subject_ref not in subjects:
            raise ValueError(f"{location} references unknown subject {subject_ref}")


def run_policy_tests(policy: dict[str, Any]) -> None:
    for test in policy["test_cases"]:
        caller = caller_from_subject(policy, test["caller"]["subject_ref"])
        expected = test["expect"]["decision"]
        if test["operation"] == "semantic_search":
            decision, allowed_tools = authorize_semantic_search(policy, caller)
            assert_decision(test["name"], decision, expected)
            for tool_name in test["expect"].get("includes", []):
                if tool_name not in allowed_tools:
                    raise AssertionError(f"{test['name']} expected search to include {tool_name}")
            for tool_name in test["expect"].get("excludes", []):
                if tool_name in allowed_tools:
                    raise AssertionError(f"{test['name']} expected search to exclude {tool_name}")
            continue

        decision = authorize_tool(policy, caller, test["tool"], test.get("input", {}))
        assert_decision(test["name"], decision, expected)


def assert_decision(test_name: str, actual: str, expected: str) -> None:
    if actual != expected:
        raise AssertionError(f"{test_name} expected {expected}, got {actual}")


def caller_from_subject(policy: dict[str, Any], subject_ref: str) -> dict[str, set[str] | str]:
    subject = policy["subjects"][subject_ref]
    entra = subject["entra"]
    return {
        "subject_ref": subject_ref,
        "client_id": first(entra.get("allowed_clients", [])),
        "scopes": set(entra.get("required_scopes", [])),
        "groups": set(entra.get("required_groups_any", [])),
        "roles": set(entra.get("required_roles_any", [])),
    }


def first(values: list[str]) -> str:
    if not values:
        raise ValueError("subject allowed_clients must not be empty")
    return values[0]


def authorize_semantic_search(
    policy: dict[str, Any],
    caller: dict[str, set[str] | str],
) -> tuple[str, list[str]]:
    search = policy["discovery"]["semantic_search"]
    if not search["enabled"]:
        return "deny", []
    if caller["subject_ref"] in set(search.get("denied_subjects", [])):
        return "deny", []
    if caller["subject_ref"] not in set(search["allowed_subjects"]):
        return "deny", []

    allowed_tools = []
    for tool_name, tool in policy["tools"].items():
        if tool_name == search["tool_name"]:
            continue
        if not tool["discovery"].get("searchable", False):
            continue
        if subject_allowed_for_tool(caller["subject_ref"], tool):
            allowed_tools.append(tool_name)
    return "allow", sorted(allowed_tools)


def authorize_tool(
    policy: dict[str, Any],
    caller: dict[str, set[str] | str],
    tool_name: str,
    tool_input: dict[str, Any],
) -> str:
    tool = policy["tools"][tool_name]
    if not subject_allowed_for_tool(caller["subject_ref"], tool):
        return "deny"

    site_refs = tool["authorization"].get("allowed_sites", [])
    if site_refs:
        site_id = str(tool_input.get("site_id", ""))
        if not site_allowed(policy, site_refs, site_id):
            return "deny"

    required_inputs = set(tool.get("input_constraints", {}).get("required", []))
    for field in required_inputs:
        if not tool_input.get(field):
            return "deny"

    input_constraints = tool.get("input_constraints", {})
    if input_constraints.get("path_must_be_under_allowed_paths"):
        resource_path = str(tool_input.get("path", ""))
        if not path_allowed(policy, site_refs, str(tool_input.get("site_id", "")), resource_path):
            return "deny"

    return "allow"


def subject_allowed_for_tool(subject_ref: str, tool: dict[str, Any]) -> bool:
    return subject_ref in set(tool["authorization"]["allowed_subjects"])


def site_allowed(policy: dict[str, Any], allowed_site_refs: list[str], site_id: str) -> bool:
    sites = policy["approved_resources"]["sharepoint_sites"]
    for site_ref in allowed_site_refs:
        if sites[site_ref]["site_id"] == site_id:
            return True
    return False


def path_allowed(
    policy: dict[str, Any],
    allowed_site_refs: list[str],
    site_id: str,
    resource_path: str,
) -> bool:
    sites = policy["approved_resources"]["sharepoint_sites"]
    site = next(
        (sites[site_ref] for site_ref in allowed_site_refs if sites[site_ref]["site_id"] == site_id),
        None,
    )
    if not site:
        return False

    requested = normalize_sharepoint_path(resource_path)
    for allowed_path in site.get("allowed_paths", []):
        allowed = normalize_sharepoint_path(str(allowed_path))
        if requested == allowed or requested.startswith(f"{allowed}/"):
            return True
    return False


def normalize_sharepoint_path(path: str) -> str:
    normalized = "/" + path.strip().strip("/")
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def render_json(policy: dict[str, Any]) -> str:
    return json.dumps(policy, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
