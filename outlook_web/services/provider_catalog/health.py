from __future__ import annotations

import copy
import re
from typing import Any

from outlook_web.errors import sanitize_error_details
from outlook_web.services.temp_mail_provider_factory import TempMailProviderFactoryError, get_available_providers

from . import catalog as _catalog
from . import integration as _integration
from . import selection as _selection
from .endpoints import (
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    _CANONICAL_EXTERNAL_ENDPOINTS,
    get_provider_documentation_contract,
)


_SECRET_FIELD_HINTS = ("key", "token", "secret", "password", "bearer")

_HEALTH_DETAIL_SECRET_HINTS = _SECRET_FIELD_HINTS + ("jwt", "authorization")
_HEALTH_DETAIL_AUTH_KEY_PATTERN = re.compile(r"(^|[_.\-\s])auth($|[_.\-\s])", re.IGNORECASE)
_HEALTH_DETAIL_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bbearer\s+\S+", re.IGNORECASE),
    re.compile(r"\bdk_[0-9a-f]{20,}\b", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)



# Bind helpers used by health/preflight projections.
get_mailbox_provider_catalog = _catalog.get_mailbox_provider_catalog
get_provider_catalog_item = _catalog.get_provider_catalog_item
_normalize_provider_name = _catalog._normalize_provider_name
_provider_diagnostic_item = _catalog._provider_diagnostic_item
get_mailbox_provider_diagnostics = _catalog.get_mailbox_provider_diagnostics
get_active_mailbox_provider_filter_contract = _catalog.get_active_mailbox_provider_filter_contract
get_mailbox_provider_deployment_profile = _catalog.get_mailbox_provider_deployment_profile
get_mailbox_provider_readiness_summary = _integration.get_mailbox_provider_readiness_summary
get_mailbox_provider_selection_policy = _selection.get_mailbox_provider_selection_policy
get_provider_integration_guide = _integration.get_provider_integration_guide

def _health_value_is_safe(key: str, value: Any) -> bool:
    lowered = str(key or "").strip().lower()
    if any(hint in lowered for hint in _HEALTH_DETAIL_SECRET_HINTS) or _HEALTH_DETAIL_AUTH_KEY_PATTERN.search(lowered):
        return False
    if isinstance(value, (dict, list, tuple, set)):
        return True
    text = str(value or "")
    if any(pattern.search(text) for pattern in _HEALTH_DETAIL_SECRET_VALUE_PATTERNS):
        return False
    return True


def _sanitize_health_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    sanitized = sanitize_error_details(value)
    if sanitized != value:
        if sanitized.strip() == "[redacted]":
            return sanitized
        return "[redacted]"
    if not _health_value_is_safe("", sanitized):
        return "[redacted]"
    return sanitized


def _sanitize_health_details(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_health_details(item) for key, item in value.items() if _health_value_is_safe(str(key), item)
        }
    if isinstance(value, list):
        return [_sanitize_health_details(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_health_details(item) for item in value]
    if isinstance(value, set):
        return [_sanitize_health_details(item) for item in sorted(value, key=str)]
    if not _health_value_is_safe("", value):
        return "[redacted]"
    return _sanitize_health_text(value)


def _provider_health_probe_result(provider_name: str) -> dict[str, Any]:
    try:
        from outlook_web.services import temp_mail_provider_factory

        provider = temp_mail_provider_factory.get_temp_mail_provider(provider_name)
        raw_result = provider.health_check()
    except TempMailProviderFactoryError as exc:
        return {
            "requested": True,
            "network_probe": False,
            "ok": False,
            "status": "error",
            "method": "provider_factory",
            "error_code": exc.code,
            "error": exc.message,
            "details": _sanitize_health_details(exc.data or {}),
        }
    except Exception as exc:
        return {
            "requested": True,
            "network_probe": True,
            "ok": False,
            "status": "error",
            "method": "health_check",
            "error_code": getattr(exc, "code", "UPSTREAM_PROBE_FAILED"),
            "error": str(getattr(exc, "message", "") or exc),
            "details": _sanitize_health_details(getattr(exc, "data", {}) or {}),
        }

    result = raw_result if isinstance(raw_result, dict) else {"success": bool(raw_result)}
    ok = bool(result.get("success", result.get("ok", False)))
    network_probe = bool(result.get("network_probe", True))
    return {
        "requested": True,
        "network_probe": network_probe,
        "ok": ok,
        "status": "ok" if ok else "error",
        "method": str(result.get("method") or "health_check"),
        "error_code": str(result.get("error_code") or ""),
        "error": str(result.get("error") or ""),
        "details": _sanitize_health_details(result.get("details") or {}),
    }


def _provider_preflight_issue_rows(
    *,
    provider_diagnostics: dict[str, Any],
    default_diagnostics: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Return compact provider preflight issue rows without secret values."""
    summary = provider_diagnostics.get("summary") if isinstance(provider_diagnostics.get("summary"), dict) else {}
    issue_rows: dict[str, list[dict[str, Any]]] = {
        "needs_config": [],
        "inactive": [],
        "unknown_filter_entries": [],
        "invalid_defaults": [],
        "inactive_defaults": [],
    }
    for item in provider_diagnostics.get("providers") or []:
        if not isinstance(item, dict):
            continue
        row = {
            "kind": item.get("kind") or "",
            "provider": item.get("provider") or "",
            "label": item.get("label") or item.get("provider") or "",
            "status": item.get("status") or "",
            "status_reason": item.get("status_reason") or "",
            "missing_config": list(item.get("missing_config") or []),
        }
        if item.get("active") and not item.get("configured"):
            issue_rows["needs_config"].append(row)
        if not item.get("active"):
            issue_rows["inactive"].append(row)

    provider_filter = provider_diagnostics.get("filter") if isinstance(provider_diagnostics.get("filter"), dict) else {}
    for provider in provider_filter.get("unknown_providers") or []:
        issue_rows["unknown_filter_entries"].append({"provider": _normalize_provider_name(provider)})

    for key in ("invalid_defaults", "inactive_defaults"):
        for item in default_diagnostics.get(key) or []:
            if isinstance(item, dict):
                issue_rows[key].append(
                    {
                        "kind": item.get("kind") or "",
                        "provider": item.get("provider") or item.get("raw_provider") or "",
                        "source": item.get("source") or "",
                        "key": item.get("key") or item.get("settings_key") or item.get("env") or "",
                        "valid": bool(item.get("valid")),
                        "active": bool(item.get("active")),
                        "config_error_code": item.get("config_error_code") or "",
                    }
                )

    if int(summary.get("needs_config") or 0) <= 0:
        issue_rows["needs_config"] = []
    if int(summary.get("inactive") or 0) <= 0:
        issue_rows["inactive"] = []
    return issue_rows


def _provider_preflight_row(health: dict[str, Any]) -> dict[str, Any]:
    """Project a single-provider health payload into the batch preflight row."""
    probe = health.get("probe") if isinstance(health.get("probe"), dict) else {}
    return {
        "kind": health.get("kind") or "",
        "provider": health.get("provider") or "",
        "label": health.get("label") or health.get("provider") or "",
        "active": bool(health.get("active")),
        "configured": bool(health.get("configured")),
        "local_ready": bool(health.get("local_ready")),
        "local_status": health.get("local_status") or "",
        "status_reason": health.get("status_reason") or "",
        "missing_config": list(health.get("missing_config") or []),
        "can_dynamic_create": bool(health.get("can_dynamic_create")),
        "can_probe_network": bool(health.get("can_probe_network")),
        "scope": copy.deepcopy(health.get("scope") or {}),
        "probe": copy.deepcopy(probe),
        "endpoints": {
            "health": PROVIDER_HEALTH_ENDPOINT,
            "preflight": PROVIDER_PREFLIGHT_ENDPOINT,
            "mailboxes": _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"],
        },
    }


def get_mailbox_provider_preflight(*, probe_network: bool = False) -> dict[str, Any]:
    """Return a secret-free batch readiness preflight for mailbox providers.

    The default path is local-only and must not instantiate providers or call
    upstream networks. Explicit probing delegates to the existing provider
    health contract so redaction and local readiness gates stay centralized.
    """
    provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
    provider_diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
    selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    integration_guide = get_provider_integration_guide(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=provider_diagnostics,
    )
    discovery = {
        "providers_endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["providers"],
        "provider_health_endpoint": PROVIDER_HEALTH_ENDPOINT,
        "provider_preflight_endpoint": PROVIDER_PREFLIGHT_ENDPOINT,
    }
    readiness_summary = get_mailbox_provider_readiness_summary(
        provider_diagnostics=provider_diagnostics,
        provider_integration_guide=integration_guide,
        selection_policy=selection_policy,
        discovery=discovery,
    )
    providers: list[dict[str, Any]] = []
    for item in provider_diagnostics.get("providers") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        provider = _normalize_provider_name(item.get("provider"))
        if not kind or not provider:
            continue
        should_probe_provider = (
            bool(probe_network) and kind == "temp" and str(item.get("status") or "").strip().lower() == "ready"
        )
        health = get_mailbox_provider_health(kind, provider, probe_network=should_probe_provider)
        if not health.get("found"):
            continue
        row = _provider_preflight_row(health)
        diagnostic_contract = item.get("contract_validation") if isinstance(item.get("contract_validation"), dict) else {}
        if diagnostic_contract:
            row["contract_validation"] = copy.deepcopy(diagnostic_contract)
        providers.append(row)

    summary_source = provider_diagnostics.get("summary") if isinstance(provider_diagnostics.get("summary"), dict) else {}
    probed = sum(1 for item in providers if (item.get("probe") or {}).get("requested"))
    probe_ok = sum(1 for item in providers if (item.get("probe") or {}).get("ok") is True)
    probe_failed = sum(1 for item in providers if (item.get("probe") or {}).get("ok") is False)
    summary = {
        "total": int(summary_source.get("total") or len(providers)),
        "active": int(summary_source.get("active") or sum(1 for item in providers if item.get("active"))),
        "ready": int(summary_source.get("ready") or sum(1 for item in providers if item.get("local_ready"))),
        "needs_config": int(
            summary_source.get("needs_config") or sum(1 for item in providers if item.get("local_status") == "needs_config")
        ),
        "inactive": int(summary_source.get("inactive") or sum(1 for item in providers if not item.get("active"))),
        "account": int(summary_source.get("account") or sum(1 for item in providers if item.get("kind") == "account")),
        "temp": int(summary_source.get("temp") or sum(1 for item in providers if item.get("kind") == "temp")),
        "dynamic_create": int(
            summary_source.get("dynamic_create") or sum(1 for item in providers if item.get("can_dynamic_create"))
        ),
        "probed": probed,
        "probe_ok": probe_ok,
        "probe_failed": probe_failed,
        "unknown_filter_entries": int(summary_source.get("unknown_filter_entries") or 0),
        "invalid_default_entries": int(summary_source.get("invalid_default_entries") or 0),
        "inactive_default_entries": int(summary_source.get("inactive_default_entries") or 0),
    }
    status = "ready"
    if summary["probe_failed"] > 0 or summary["unknown_filter_entries"] > 0 or summary["invalid_default_entries"] > 0:
        status = "degraded"
    elif summary["needs_config"] > 0 or summary["active"] <= 0:
        status = "needs_config"

    defaults = provider_diagnostics.get("defaults") if isinstance(provider_diagnostics.get("defaults"), dict) else {}
    return {
        "version": 1,
        "status": status,
        "scope": {
            "type": "local_config" if not probe_network else "local_config_with_explicit_provider_probe",
            "network_probe": bool(probe_network),
            "description": "Batch provider preflight uses local provider discovery by default and only probes upstream provider health when probe_network=true.",
        },
        "summary": summary,
        "issues": _provider_preflight_issue_rows(provider_diagnostics=provider_diagnostics, default_diagnostics=defaults),
        "defaults": copy.deepcopy(defaults),
        "filter": copy.deepcopy(provider_filter),
        "endpoints": {
            "providers": _CANONICAL_EXTERNAL_ENDPOINTS["providers"],
            "provider_health": PROVIDER_HEALTH_ENDPOINT,
            "provider_preflight": PROVIDER_PREFLIGHT_ENDPOINT,
            "mailboxes": _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"],
            "openapi": _CANONICAL_EXTERNAL_ENDPOINTS["openapi"],
        },
        "providers": providers,
        "readiness_summary": readiness_summary,
        "documentation": get_provider_documentation_contract(),
    }


def get_mailbox_provider_health(kind: str, provider_name: str | None, *, probe_network: bool = False) -> dict[str, Any]:
    item = get_provider_catalog_item(kind, provider_name, include_inactive=True)
    if item is None:
        return {
            "found": False,
            "kind": str(kind or "").strip().lower(),
            "provider": _normalize_provider_name(provider_name),
            "error_code": "MAILBOX_PROVIDER_NOT_FOUND",
        }

    diagnostic = _provider_diagnostic_item(item)
    local_ready = diagnostic["status"] == "ready"
    can_probe_network = item.get("kind") == "temp" and local_ready
    probe = {
        "requested": bool(probe_network),
        "network_probe": False,
        "ok": None,
        "status": "not_requested",
        "method": "",
        "error_code": "",
        "error": "",
        "details": {},
    }
    if probe_network and not can_probe_network:
        probe_error_code = "PROVIDER_PROBE_NOT_SUPPORTED"
        if item.get("kind") == "temp":
            probe_error_code = (
                "TEMP_MAIL_PROVIDER_NOT_CONFIGURED" if bool(item.get("active", True)) else "MAILBOX_PROVIDER_NOT_ACTIVE"
            )
        probe.update(
            {
                "status": "skipped",
                "ok": False,
                "error_code": probe_error_code,
                "error": "Provider is not locally ready for upstream probe",
            }
        )
    elif probe_network:
        probe = _provider_health_probe_result(str(item.get("provider") or ""))

    return {
        "found": True,
        "kind": diagnostic["kind"],
        "provider": diagnostic["provider"],
        "label": diagnostic["label"],
        "active": diagnostic["active"],
        "configured": diagnostic["configured"],
        "local_ready": local_ready,
        "local_status": diagnostic["status"],
        "status_reason": diagnostic["status_reason"],
        "missing_config": diagnostic["missing_config"],
        "can_dynamic_create": diagnostic["can_dynamic_create"],
        "can_probe_network": can_probe_network,
        "scope": {
            "local_config": True,
            "network_probe": bool(probe.get("network_probe")),
            "network_probe_requested": bool(probe_network),
        },
        "probe": probe,
    }

