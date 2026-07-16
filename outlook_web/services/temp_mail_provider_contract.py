from __future__ import annotations

import inspect
import re
from typing import Any

from outlook_web.services.temp_mail_provider_base import TempMailProviderBase, normalize_provider_capabilities

CONTRACT_VERSION = 1

_PROVIDER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_CONFIG_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_KNOWN_CONFIG_FIELD_TYPES = {"text", "password", "textarea", "number", "select", "url", "toggle", "checkbox"}
_SECRET_FIELD_HINTS = (
    "api_key",
    "apikey",
    "bearer",
    "consumer_key",
    "jwt",
    "password",
    "secret",
    "task_token",
    "token",
)
_REQUIRED_METHODS = (
    "get_options",
    "create_mailbox",
    "delete_mailbox",
    "list_messages",
    "get_message_detail",
    "delete_message",
    "clear_messages",
)


def _derive_provider_name(provider_cls: type[Any]) -> str:
    class_name = getattr(provider_cls, "__name__", "")
    if not class_name:
        return ""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower().strip("_")


def _field_is_secret(field: dict[str, Any]) -> bool:
    field_type = str(field.get("type") or "").strip().lower()
    field_key = str(field.get("key") or "").strip().lower()
    return field_type == "password" or any(hint in field_key for hint in _SECRET_FIELD_HINTS)


def _add_issue(issues: list[dict[str, Any]], code: str, severity: str, path: str, message: str) -> None:
    issues.append(
        {
            "code": code,
            "severity": severity,
            "path": path,
            "message": message,
        }
    )


def _add_check(checks: list[dict[str, Any]], key: str, ok: bool, *, detail: str = "") -> None:
    check: dict[str, Any] = {"key": key, "ok": bool(ok)}
    if detail:
        check["detail"] = detail
    checks.append(check)


def _safe_config_schema_fields(
    schema: Any, issues: list[dict[str, Any]], checks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if schema in (None, ""):
        _add_check(checks, "config_schema", True, detail="empty")
        return []
    if not isinstance(schema, dict):
        _add_issue(issues, "CONFIG_SCHEMA_INVALID", "error", "config_schema", "config_schema must be an object")
        _add_check(checks, "config_schema", False)
        return []

    fields = schema.get("fields", [])
    if fields in (None, ""):
        fields = []
    if not isinstance(fields, list):
        _add_issue(issues, "CONFIG_FIELDS_INVALID", "error", "config_schema.fields", "config_schema.fields must be a list")
        _add_check(checks, "config_schema", False)
        return []

    _add_check(checks, "config_schema", True, detail=f"fields={len(fields)}")
    safe_fields: list[dict[str, Any]] = []
    for index, raw_field in enumerate(fields):
        path = f"config_schema.fields[{index}]"
        if not isinstance(raw_field, dict):
            _add_issue(issues, "CONFIG_FIELD_INVALID", "error", path, "config field must be an object")
            continue

        key = str(raw_field.get("key") or "").strip()
        if not key:
            _add_issue(issues, "CONFIG_FIELD_KEY_MISSING", "error", f"{path}.key", "config field key is required")
        elif not _CONFIG_KEY_PATTERN.match(key):
            _add_issue(issues, "CONFIG_FIELD_KEY_INVALID", "error", f"{path}.key", "config field key must be stable ASCII")

        field_type = str(raw_field.get("type") or "text").strip().lower() or "text"
        if field_type not in _KNOWN_CONFIG_FIELD_TYPES:
            _add_issue(
                issues,
                "CONFIG_FIELD_TYPE_UNKNOWN",
                "warning",
                f"{path}.type",
                "config field type is not recognized by the plugin UI",
            )

        safe_field: dict[str, Any] = {
            "key": key,
            "label": str(raw_field.get("label") or key).strip(),
            "type": field_type,
            "required": bool(raw_field.get("required")),
            "secret": _field_is_secret({**raw_field, "type": field_type, "key": key}),
        }
        if "default" in raw_field:
            if safe_field["secret"]:
                _add_issue(
                    issues,
                    "CONFIG_FIELD_SECRET_DEFAULT",
                    "error",
                    f"{path}.default",
                    "secret config fields must not define default values",
                )
            else:
                safe_field["default"] = raw_field.get("default")
        safe_fields.append(safe_field)
    return safe_fields


def _method_is_implemented(provider_cls: type[Any], method_name: str) -> bool:
    method = getattr(provider_cls, method_name, None)
    if not callable(method):
        return False
    abstract_methods = getattr(provider_cls, "__abstractmethods__", set()) or set()
    if method_name in abstract_methods:
        return False
    base_method = getattr(TempMailProviderBase, method_name, None)
    if method is base_method:
        return False
    return True


def _is_temp_mail_provider_base_subclass(provider_cls: type[Any]) -> bool:
    try:
        return issubclass(provider_cls, TempMailProviderBase)
    except TypeError:
        return False


def _instantiate_provider(provider_name: str, provider_cls: type[Any]) -> Any:
    try:
        return provider_cls(provider_name=provider_name)
    except TypeError:
        return provider_cls()


def _probe_options(
    provider_name: str, provider_cls: type[Any], issues: list[dict[str, Any]], checks: list[dict[str, Any]]
) -> dict[str, Any]:
    if not callable(getattr(provider_cls, "get_options", None)):
        return {"requested": True, "ok": False, "return_type": "missing"}
    try:
        provider = _instantiate_provider(provider_name, provider_cls)
        options = provider.get_options()
    except Exception as exc:
        _add_issue(
            issues,
            "OPTIONS_PROBE_FAILED",
            "warning",
            "get_options",
            f"get_options probe failed: {type(exc).__name__}",
        )
        _add_check(checks, "get_options_probe", False, detail=type(exc).__name__)
        return {"requested": True, "ok": False, "return_type": "error", "error_type": type(exc).__name__}

    if not isinstance(options, dict):
        _add_issue(issues, "OPTIONS_RETURN_INVALID", "error", "get_options", "get_options must return an object")
        _add_check(checks, "get_options_probe", False, detail=type(options).__name__)
        return {"requested": True, "ok": False, "return_type": type(options).__name__}

    domains = options.get("domains") if isinstance(options.get("domains"), list) else []
    _add_check(checks, "get_options_probe", True, detail="dict")
    return {
        "requested": True,
        "ok": True,
        "return_type": "dict",
        "domain_count": len(domains),
        "configured": bool(options.get("configured", True)),
    }


def _status_from_issues(issues: list[dict[str, Any]]) -> tuple[str, bool, int, int]:
    errors = len([item for item in issues if item.get("severity") == "error"])
    warnings = len([item for item in issues if item.get("severity") == "warning"])
    if errors:
        return "invalid", False, errors, warnings
    if warnings:
        return "warning", True, errors, warnings
    return "valid", True, errors, warnings


def validate_temp_mail_provider_class(
    provider_name: str,
    provider_cls: type[Any],
    *,
    probe_options: bool = False,
) -> dict[str, Any]:
    registry_name = str(provider_name or "").strip()
    explicit_provider_name = "provider_name" in getattr(provider_cls, "__dict__", {})
    raw_provider_name = getattr(provider_cls, "provider_name", "")
    declared_provider_name = str(raw_provider_name or "").strip() if isinstance(raw_provider_name, str) else ""
    resolved_provider_name = (
        declared_provider_name or (registry_name if not explicit_provider_name else "") or _derive_provider_name(provider_cls)
    )

    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    inherits_base_class = _is_temp_mail_provider_base_subclass(provider_cls)
    _add_check(checks, "base_class", inherits_base_class)
    if not inherits_base_class:
        _add_issue(
            issues,
            "PROVIDER_BASE_CLASS_INVALID",
            "error",
            "provider_class",
            "provider class must inherit TempMailProviderBase",
        )

    if not registry_name:
        _add_issue(issues, "PROVIDER_NAME_MISSING", "error", "provider", "provider registry name is required")
    elif not _PROVIDER_NAME_PATTERN.match(registry_name):
        _add_issue(issues, "PROVIDER_NAME_INVALID", "error", "provider", "provider registry name must be stable ASCII")

    if not resolved_provider_name:
        _add_issue(issues, "PROVIDER_NAME_MISSING", "error", "provider_name", "provider_name is required")
    elif resolved_provider_name != registry_name:
        _add_issue(
            issues, "PROVIDER_NAME_MISMATCH", "error", "provider_name", "provider_name must match the registered provider key"
        )
    elif not declared_provider_name and not explicit_provider_name:
        _add_issue(issues, "PROVIDER_NAME_DERIVED", "warning", "provider_name", "provider_name is derived from the class name")
    _add_check(checks, "provider_name", bool(registry_name and resolved_provider_name == registry_name))

    label = str(getattr(provider_cls, "provider_label", "") or "").strip()
    if not label:
        _add_issue(issues, "PROVIDER_LABEL_MISSING", "warning", "provider_label", "provider_label is recommended")
    _add_check(checks, "provider_label", bool(label))

    version = str(getattr(provider_cls, "provider_version", "") or "").strip()
    if not version:
        _add_issue(issues, "PROVIDER_VERSION_MISSING", "error", "provider_version", "provider_version is required")
    _add_check(checks, "provider_version", bool(version))

    capabilities = normalize_provider_capabilities(getattr(provider_cls, "provider_capabilities", None))
    _add_check(checks, "capabilities", set(capabilities.keys()) == {"delete_mailbox", "delete_message", "clear_messages"})

    safe_config_fields = _safe_config_schema_fields(getattr(provider_cls, "config_schema", {}), issues, checks)

    implemented_methods: dict[str, bool] = {}
    for method_name in _REQUIRED_METHODS:
        implemented = _method_is_implemented(provider_cls, method_name)
        implemented_methods[method_name] = implemented
        _add_check(checks, f"method.{method_name}", implemented)
        if not implemented:
            _add_issue(issues, "METHOD_NOT_IMPLEMENTED", "error", method_name, f"{method_name} must be implemented")

    options_probe = {"requested": False, "ok": None}
    if probe_options:
        options_probe = _probe_options(registry_name or resolved_provider_name, provider_cls, issues, checks)

    status, valid, error_count, warning_count = _status_from_issues(issues)
    return {
        "version": CONTRACT_VERSION,
        "provider": registry_name or resolved_provider_name,
        "status": status,
        "valid": valid,
        "checks": checks,
        "issues": issues,
        "summary": {"errors": error_count, "warnings": warning_count, "checks": len(checks)},
        "safe_metadata": {
            "provider_name": resolved_provider_name,
            "label": label,
            "version": version,
            "author": str(getattr(provider_cls, "provider_author", "") or ""),
            "capabilities": capabilities,
            "config_fields": safe_config_fields,
            "implemented_methods": implemented_methods,
            "options_probe": options_probe,
        },
    }


def validate_temp_mail_provider_info(provider_info: dict[str, Any]) -> dict[str, Any]:
    existing = provider_info.get("contract_validation") if isinstance(provider_info, dict) else None
    if isinstance(existing, dict) and existing.get("version") == CONTRACT_VERSION:
        return existing
    name = str((provider_info or {}).get("name") or (provider_info or {}).get("provider") or "").strip()
    issues: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    if not name:
        _add_issue(issues, "PROVIDER_NAME_MISSING", "error", "name", "provider name is required")
    _add_check(checks, "provider_name", bool(name))
    safe_config_fields = _safe_config_schema_fields((provider_info or {}).get("config_schema") or {}, issues, checks)
    status, valid, error_count, warning_count = _status_from_issues(issues)
    return {
        "version": CONTRACT_VERSION,
        "provider": name,
        "status": status,
        "valid": valid,
        "checks": checks,
        "issues": issues,
        "summary": {"errors": error_count, "warnings": warning_count, "checks": len(checks)},
        "safe_metadata": {
            "provider_name": name,
            "label": str((provider_info or {}).get("label") or name),
            "version": str((provider_info or {}).get("version") or ""),
            "author": str((provider_info or {}).get("author") or ""),
            "capabilities": normalize_provider_capabilities((provider_info or {}).get("capabilities")),
            "config_fields": safe_config_fields,
            "implemented_methods": {},
            "options_probe": {"requested": False, "ok": None},
        },
    }


def contract_validation_summary(validation: dict[str, Any] | None) -> dict[str, Any]:
    source = validation if isinstance(validation, dict) else {}
    return {
        "version": int(source.get("version") or CONTRACT_VERSION),
        "provider": str(source.get("provider") or ""),
        "status": str(source.get("status") or "unknown"),
        "valid": bool(source.get("valid")),
        "summary": dict(source.get("summary") or {"errors": 0, "warnings": 0, "checks": 0}),
        "issue_codes": [str(item.get("code") or "") for item in (source.get("issues") or []) if isinstance(item, dict)],
    }


def sanitize_config_schema(schema: Any) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    result = {key: value for key, value in schema.items() if key != "fields"}
    fields = schema.get("fields") if isinstance(schema.get("fields"), list) else []
    safe_fields: list[dict[str, Any]] = []
    for raw_field in fields:
        if not isinstance(raw_field, dict):
            continue
        field = dict(raw_field)
        if _field_is_secret(field):
            field.pop("default", None)
        safe_fields.append(field)
    result["fields"] = safe_fields
    return result
