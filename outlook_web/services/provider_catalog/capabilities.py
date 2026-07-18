from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from typing import Any

from outlook_web import config
from outlook_web.cors_config import get_external_api_cors_contract
from outlook_web.errors import sanitize_error_details
from outlook_web.repositories import settings as settings_repo
from outlook_web.services.mailbox_directory_contract import get_mailbox_catalog_contract
from outlook_web.services.providers import MAIL_PROVIDERS, get_provider_list
from outlook_web.services.temp_mail_provider_base import normalize_provider_capabilities
from outlook_web.services.temp_mail_provider_factory import TempMailProviderFactoryError, get_available_providers

from .bridge import (
    _canonical_bridge_operator_provider,
    _collapse_bridge_operator_provider_rows,
    _merge_unique_str_list,
    get_operator_temp_mail_default_provider,
)
from .catalog import (
    get_active_mailbox_provider_filter_contract,
    get_mailbox_provider_catalog,
    get_mailbox_provider_default_diagnostics,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_provider_alias_contract,
    get_provider_catalog_item,
)
from .constants import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    PROVIDER_SELECTION_SOURCE_PRIORITY,
    TEMP_MAIL_PROVIDER_ENV,
)
from .endpoints import (
    _CANONICAL_EXTERNAL_ENDPOINTS,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    _action_contract_next_actions_for_endpoint_map,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_api_legacy_endpoint_map,
    get_external_mailbox_read_contract,
    get_provider_documentation_contract,
)
from .health import _sanitize_health_text
from .integration import (
    get_external_integration_manifest,
    get_mailbox_directory_provider_context,
    get_mailbox_provider_readiness_summary,
    get_provider_integration_guide,
)
from .selection import get_mailbox_provider_selection_policy


def get_external_api_capabilities_contract(*, consumer: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the machine-readable discovery contract for the external API."""
    public_mode = settings_repo.get_external_api_public_mode()
    consumer = consumer or {}
    pool_external_enabled = settings_repo.get_pool_external_enabled()
    pool_consumer_has_access = bool(consumer.get("is_legacy")) or bool(consumer.get("pool_access"))

    pool_restrictions: list[str] = []
    read_contract = get_external_mailbox_read_contract(lifecycle="none")
    pool_read_contract = get_external_mailbox_read_contract(lifecycle="pool_claim")
    task_temp_read_contract = get_external_mailbox_read_contract(lifecycle="task_temp_mailbox")
    mailbox_directory_contract = get_mailbox_catalog_contract()
    read_endpoints = read_contract.get("read_endpoints") or {}
    endpoints = {
        **get_external_api_endpoint_map(),
        **{key: str(value) for key, value in read_endpoints.items() if key in _CANONICAL_EXTERNAL_ENDPOINTS},
    }
    compatibility = get_external_api_compatibility_contract()
    cors_contract = get_external_api_cors_contract()

    feature_available = {
        "message_list": True,
        "message_detail": True,
        "raw_content": True,
        "verification_code": True,
        "verification_link": True,
        "wait_message": True,
        "openapi_contract": True,
        "mailbox_directory": True,
        "provider_discovery": True,
        "provider_health": True,
        "provider_preflight": True,
        "api_docs": True,
        "mailbox_session_start": True,
        "mailbox_session_read": True,
        "mailbox_session_close": True,
        "task_temp_mailbox_apply": True,
        "task_temp_mailbox_finish": True,
        "pool_claim_random": pool_external_enabled and pool_consumer_has_access,
        "pool_claim_release": pool_external_enabled and pool_consumer_has_access,
        "pool_claim_complete": pool_external_enabled and pool_consumer_has_access,
        "pool_stats": pool_external_enabled and pool_consumer_has_access,
    }

    if not pool_external_enabled:
        pool_restrictions.append("external_pool_disabled")
    if not pool_consumer_has_access:
        pool_restrictions.append("pool_access_required")

    if public_mode:
        if settings_repo.get_external_api_disable_raw_content():
            feature_available["raw_content"] = False
        if settings_repo.get_external_api_disable_wait_message():
            feature_available["wait_message"] = False
        pool_guard_settings = {
            "pool_claim_random": settings_repo.get_external_api_disable_pool_claim_random(),
            "pool_claim_release": settings_repo.get_external_api_disable_pool_claim_release(),
            "pool_claim_complete": settings_repo.get_external_api_disable_pool_claim_complete(),
            "pool_stats": settings_repo.get_external_api_disable_pool_stats(),
        }
        for feature, disabled in pool_guard_settings.items():
            if disabled:
                feature_available[feature] = False
                pool_restrictions.append(f"{feature}_disabled")

    available = [feature for feature, enabled in feature_available.items() if enabled]
    restricted = [feature for feature, enabled in feature_available.items() if not enabled]
    if "pool_access_required" in pool_restrictions:
        restricted.append("pool_access_required")

    pool_features = [
        feature
        for feature in ("pool_claim_random", "pool_claim_release", "pool_claim_complete", "pool_stats")
        if feature_available.get(feature)
    ]
    pool_default_provider = settings_repo.get_pool_default_provider(strict=False) or "auto"
    temp_mail_provider = get_operator_temp_mail_default_provider(strict=False)
    provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    provider_diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
    deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
    selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    integration_guide = get_provider_integration_guide(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=provider_diagnostics,
        endpoints=endpoints,
    )
    integration_manifest = get_external_integration_manifest(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=provider_diagnostics,
        provider_integration_guide=integration_guide,
        endpoints=endpoints,
    )
    return {
        "public_mode": public_mode,
        "features": available,
        "available_features": available,
        "restricted_features": restricted,
        "defaults": {
            "pool_claim_provider": pool_default_provider,
            "pool_claim_provider_env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
            "temp_mail_provider": temp_mail_provider,
            "temp_mail_provider_env": TEMP_MAIL_PROVIDER_ENV,
            "active_mailbox_providers": provider_filter["active_providers"],
            "active_mailbox_provider_env": ACTIVE_MAILBOX_PROVIDER_ENV,
        },
        "deployment_env": copy.deepcopy(DEPLOYMENT_ENV_CONTRACT),
        "deployment_profile": deployment_profile,
        "selection_policy": selection_policy,
        "provider_integration_guide": integration_guide,
        "integration_manifest": integration_manifest,
        "quickstart": copy.deepcopy(integration_manifest.get("quickstart") or {}),
        "compatibility": compatibility,
        "cors": cors_contract,
        "legacy_endpoints": copy.deepcopy(compatibility["legacy_endpoints"]),
        "documentation": get_provider_documentation_contract(),
        "provider_filter": provider_filter,
        "provider_diagnostics": {
            "summary": provider_diagnostics["summary"],
            "filter": provider_diagnostics["filter"],
            "defaults": provider_diagnostics["defaults"],
            "scope": provider_diagnostics["scope"],
        },
        "endpoints": endpoints,
        "mailbox_directory": {
            "endpoint": endpoints["mailboxes"],
            "query_fields": ["kind", "status", "read_capability", "action", "provider", "search", "sort", "page", "page_size"],
            "response_contract": "unified_mailbox_directory",
            "contract": mailbox_directory_contract,
            "kind_definitions": copy.deepcopy(mailbox_directory_contract.get("kind_definitions") or []),
            "status_definitions": copy.deepcopy(mailbox_directory_contract.get("status_definitions") or []),
            "read_capability_definitions": copy.deepcopy(mailbox_directory_contract.get("read_capability_definitions") or []),
            "action_definitions": copy.deepcopy(mailbox_directory_contract.get("action_definitions") or []),
            "sort_definitions": copy.deepcopy(mailbox_directory_contract.get("sort_definitions") or []),
            "summary_fields": copy.deepcopy(mailbox_directory_contract.get("summary_fields") or []),
            "quick_view_presets": copy.deepcopy(mailbox_directory_contract.get("quick_view_presets") or []),
            "provider_context_field": "provider_context",
            "item_action_contract_field": "action_contract",
            "item_action_contract_source": "provider_catalog.external_mailbox_read_contract",
            "account_scope": "allowed_emails_before_pagination_when_configured",
        },
        "integration_bundle": {
            "endpoint": endpoints["integration_bundle"],
            "response_contract": "integration_bundle",
            "recommended_for": ["external_service_onboarding", "smoke_check", "client_generation"],
        },
        "external_mailbox_read_contract": read_contract,
        "mailbox_session": {
            "start_endpoint": endpoints["mailbox_session_start"],
            "read_endpoint": endpoints["mailbox_session_read"],
            "close_endpoint": endpoints["mailbox_session_close"],
            "start_fields": [
                "caller_id",
                "task_id",
                "source_strategy",
                "provider",
                "provider_name",
                "email_domain",
                "project_key",
                "prefix",
                "domain",
            ],
            "close_fields": [
                "session_type",
                "account_id",
                "claim_token",
                "task_token",
                "caller_id",
                "task_id",
                "result",
                "detail",
                "reason",
            ],
            "read_fields": [
                "session_type",
                "read_action",
                "caller_id",
                "task_id",
                "email",
                "claim_token",
                "task_token",
                "message_id",
                "folder",
                "skip",
                "top",
                "from_contains",
                "subject_contains",
                "since_minutes",
                "code_length",
                "code_regex",
                "code_source",
                "timeout_seconds",
                "poll_interval",
                "mode",
            ],
            "read_action_values": [
                "messages",
                "latest_message",
                "message_detail",
                "message_raw",
                "verification_code",
                "verification_link",
                "wait_message",
            ],
            "source_strategy_values": ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
            "read_contract": read_contract,
        },
        "pool": {
            "external_enabled": pool_external_enabled,
            "current_consumer_has_access": pool_consumer_has_access,
            "requires_pool_access": True,
            "default_provider": pool_default_provider,
            "default_provider_env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
            "restrictions": pool_restrictions,
            "features": pool_features,
            "claim_endpoint": endpoints["pool_claim_random"],
            "claim_fields": ["caller_id", "task_id", "provider", "email_domain", "project_key"],
            "release_endpoint": endpoints["pool_claim_release"],
            "release_fields": ["account_id", "claim_token", "caller_id", "task_id", "reason"],
            "complete_endpoint": endpoints["pool_claim_complete"],
            "complete_fields": ["account_id", "claim_token", "caller_id", "task_id", "result", "detail"],
            "stats_endpoint": endpoints["pool_stats"],
            "read_contract": pool_read_contract,
        },
        "task_temp_mailbox": {
            "apply_endpoint": endpoints["temp_mail_apply"],
            "apply_fields": ["caller_id", "task_id", "prefix", "domain", "provider_name"],
            "finish_endpoint": endpoints["temp_mail_finish"],
            "finish_fields": ["result", "detail"],
            "read_contract": task_temp_read_contract,
        },
    }


def get_external_api_readiness_summary(
    *,
    consumer: dict[str, Any] | None = None,
    database_ok: bool = True,
    upstream_probe_ok: bool | None = None,
) -> dict[str, Any]:
    """Return a compact, secret-free health readiness summary.

    The full discovery contract remains owned by capabilities/providers. Health
    only projects the fields an external integrator needs before deciding which
    discovery endpoint to call next.
    """
    cors_contract = get_external_api_cors_contract()
    try:
        capabilities = get_external_api_capabilities_contract(consumer=consumer)
    except Exception as exc:
        return {
            "status": "degraded",
            "database": "ok" if database_ok else "error",
            "upstream_probe": _readiness_upstream_probe_status(upstream_probe_ok),
            "discovery": {"status": "unavailable", "next_endpoints": {}},
            "providers": {"status": "unknown", "summary": {}},
            "mailbox_directory": _external_mailbox_directory_readiness_unavailable(),
            "pool": {"status": "unknown", "restrictions": []},
            "task_temp_mailbox": {"status": "unknown"},
            "cors": copy.deepcopy(cors_contract),
            "warnings": ["capabilities_unavailable"],
            "error_code": type(exc).__name__,
            "error": _sanitize_health_text(str(exc)),
        }

    endpoints = capabilities.get("endpoints") if isinstance(capabilities.get("endpoints"), dict) else {}
    provider_diagnostics = (
        capabilities.get("provider_diagnostics") if isinstance(capabilities.get("provider_diagnostics"), dict) else {}
    )
    provider_summary = provider_diagnostics.get("summary") if isinstance(provider_diagnostics.get("summary"), dict) else {}
    provider_filter = capabilities.get("provider_filter") if isinstance(capabilities.get("provider_filter"), dict) else {}
    pool = capabilities.get("pool") if isinstance(capabilities.get("pool"), dict) else {}
    task_temp_mailbox = (
        capabilities.get("task_temp_mailbox") if isinstance(capabilities.get("task_temp_mailbox"), dict) else {}
    )
    defaults = capabilities.get("defaults") if isinstance(capabilities.get("defaults"), dict) else {}

    warnings = _readiness_warnings(
        database_ok=database_ok,
        upstream_probe_ok=upstream_probe_ok,
        provider_summary=provider_summary,
        pool=pool,
    )
    provider_status = _readiness_provider_status(provider_summary)
    pool_status = _readiness_pool_status(pool)
    task_temp_status = _readiness_task_temp_status(provider_summary, capabilities.get("available_features") or [])
    mailbox_directory = _external_mailbox_directory_readiness(
        consumer=consumer,
        endpoint=endpoints.get("mailboxes", _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
    )
    overall_status = "ready"
    if (
        not database_ok
        or provider_status in {"needs_config", "inactive", "unknown"}
        or pool_status == "degraded"
        or mailbox_directory.get("status") == "degraded"
    ):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "database": "ok" if database_ok else "error",
        "upstream_probe": _readiness_upstream_probe_status(upstream_probe_ok),
        "discovery": {
            "status": "ready",
            "next_endpoints": {
                "capabilities": endpoints.get("capabilities", _CANONICAL_EXTERNAL_ENDPOINTS["capabilities"]),
                "integration_bundle": endpoints.get("integration_bundle", _CANONICAL_EXTERNAL_ENDPOINTS["integration_bundle"]),
                "docs": endpoints.get("docs", _CANONICAL_EXTERNAL_ENDPOINTS["docs"]),
                "providers": endpoints.get("providers", _CANONICAL_EXTERNAL_ENDPOINTS["providers"]),
                "mailboxes": endpoints.get("mailboxes", _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
                "openapi": endpoints.get("openapi", _CANONICAL_EXTERNAL_ENDPOINTS["openapi"]),
            },
        },
        "providers": {
            "status": provider_status,
            "summary": {
                "total": int(provider_summary.get("total") or 0),
                "active": int(provider_summary.get("active") or 0),
                "ready": int(provider_summary.get("ready") or 0),
                "needs_config": int(provider_summary.get("needs_config") or 0),
                "dynamic_create": int(provider_summary.get("dynamic_create") or 0),
                "account": int(provider_summary.get("account") or 0),
                "temp": int(provider_summary.get("temp") or 0),
                "unknown_filter_entries": int(provider_summary.get("unknown_filter_entries") or 0),
                "invalid_default_entries": int(provider_summary.get("invalid_default_entries") or 0),
                "inactive_default_entries": int(provider_summary.get("inactive_default_entries") or 0),
            },
            "filter_mode": str(provider_filter.get("mode") or "all"),
            "active_allowlist": list(defaults.get("active_mailbox_providers") or []),
        },
        "mailbox_directory": mailbox_directory,
        "pool": {
            "status": pool_status,
            "external_enabled": bool(pool.get("external_enabled")),
            "current_consumer_has_access": bool(pool.get("current_consumer_has_access")),
            "default_provider": str(pool.get("default_provider") or "auto"),
            "restrictions": list(pool.get("restrictions") or []),
            "claim_endpoint": str(
                pool.get("claim_endpoint")
                or endpoints.get("pool_claim_random")
                or _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_random"]
            ),
        },
        "task_temp_mailbox": {
            "status": task_temp_status,
            "default_provider": str(defaults.get("temp_mail_provider") or ""),
            "provider_selector_field": "provider_name",
            "apply_endpoint": str(
                task_temp_mailbox.get("apply_endpoint")
                or endpoints.get("temp_mail_apply")
                or _CANONICAL_EXTERNAL_ENDPOINTS["temp_mail_apply"]
            ),
            "finish_endpoint": str(
                task_temp_mailbox.get("finish_endpoint")
                or endpoints.get("temp_mail_finish")
                or _CANONICAL_EXTERNAL_ENDPOINTS["temp_mail_finish"]
            ),
        },
        "cors": copy.deepcopy(cors_contract),
        "warnings": list(dict.fromkeys([*warnings, *list(mailbox_directory.get("warnings") or [])])),
    }


def _external_mailbox_directory_readiness(
    *,
    consumer: dict[str, Any] | None,
    endpoint: str = _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"],
) -> dict[str, Any]:
    allowed_emails = [
        str(item or "").strip() for item in ((consumer or {}).get("allowed_emails") or []) if str(item or "").strip()
    ]
    try:
        from outlook_web.services.mailbox_catalog import list_unified_mailboxes

        payload = list_unified_mailboxes(page=1, page_size=1, allowed_account_emails=allowed_emails)
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
        total_count = int(pagination.get("total_count") or 0)
        account_count = int(summary.get("account") or 0)
        temp_count = int(summary.get("temp") or 0)
        if total_count > 0:
            status = "ready"
        elif allowed_emails:
            status = "restricted"
        else:
            status = "empty"
        return {
            "status": status,
            "endpoint": str(endpoint or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
            "scoped": bool(allowed_emails),
            "summary": dict(summary),
            "totals": {
                "mailboxes": total_count,
                "account_mailboxes": account_count,
                "temp_mailboxes": temp_count,
            },
            "quick_probe_params": _external_mailbox_directory_quick_probe_params(),
        }
    except Exception:
        return _external_mailbox_directory_readiness_unavailable(endpoint=endpoint, scoped=bool(allowed_emails))


def _external_mailbox_directory_readiness_unavailable(
    *,
    endpoint: str = _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"],
    scoped: bool = False,
) -> dict[str, Any]:
    return {
        "status": "degraded",
        "endpoint": str(endpoint or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
        "scoped": bool(scoped),
        "summary": {},
        "totals": {
            "mailboxes": 0,
            "account_mailboxes": 0,
            "temp_mailboxes": 0,
        },
        "quick_probe_params": _external_mailbox_directory_quick_probe_params(),
        "warnings": ["mailbox_directory_unavailable"],
    }


def _external_mailbox_directory_quick_probe_params() -> dict[str, Any]:
    return {
        "page": 1,
        "page_size": 1,
        "kind": "all",
        "status": "all",
        "read_capability": "all",
        "action": "all",
        "provider": "all",
        "sort": "updated_desc",
    }


def _readiness_upstream_probe_status(upstream_probe_ok: bool | None) -> dict[str, Any]:
    if upstream_probe_ok is True:
        status = "ok"
    elif upstream_probe_ok is False:
        status = "error"
    else:
        status = "unknown"
    return {"status": status, "ok": upstream_probe_ok}


def _readiness_provider_status(provider_summary: dict[str, Any]) -> str:
    if not provider_summary:
        return "unknown"
    if int(provider_summary.get("active") or 0) <= 0:
        return "inactive"
    if int(provider_summary.get("ready") or 0) > 0:
        return "ready"
    if int(provider_summary.get("needs_config") or 0) > 0:
        return "needs_config"
    return "unknown"


def _readiness_pool_status(pool: dict[str, Any]) -> str:
    if not bool(pool.get("external_enabled")):
        return "disabled"
    if not bool(pool.get("current_consumer_has_access")):
        return "restricted"
    features = set(pool.get("features") or [])
    if {"pool_claim_random", "pool_claim_release", "pool_claim_complete"}.issubset(features):
        return "ready"
    return "degraded"


def _readiness_task_temp_status(provider_summary: dict[str, Any], available_features: list[Any]) -> str:
    if "task_temp_mailbox_apply" not in {str(item) for item in available_features}:
        return "restricted"
    if int(provider_summary.get("dynamic_create") or 0) > 0 and int(provider_summary.get("ready") or 0) > 0:
        return "ready"
    if int(provider_summary.get("needs_config") or 0) > 0:
        return "needs_config"
    return "ready"


def _readiness_warnings(
    *,
    database_ok: bool,
    upstream_probe_ok: bool | None,
    provider_summary: dict[str, Any],
    pool: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not database_ok:
        warnings.append("database_error")
    if upstream_probe_ok is False:
        warnings.append("upstream_probe_failed")
    if int(provider_summary.get("unknown_filter_entries") or 0) > 0:
        warnings.append("unknown_active_provider_filter_entries")
    if int(provider_summary.get("invalid_default_entries") or 0) > 0:
        warnings.append("invalid_default_provider_entries")
    if int(provider_summary.get("inactive_default_entries") or 0) > 0:
        warnings.append("inactive_default_provider_entries")
    if int(provider_summary.get("needs_config") or 0) > 0:
        warnings.append("provider_config_required")
    for restriction in pool.get("restrictions") or []:
        text = str(restriction or "").strip()
        if text:
            warnings.append(text)
    return list(dict.fromkeys(warnings))


def get_external_api_integration_bundle(
    *,
    consumer: dict[str, Any] | None = None,
    service: str = "mailops",
    version: str = "",
    database_ok: bool = True,
    upstream_probe_ok: bool | None = None,
    openapi_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a secret-safe readiness bundle for external integrations."""

    capabilities = get_external_api_capabilities_contract(consumer=consumer)
    endpoints = capabilities.get("endpoints") if isinstance(capabilities.get("endpoints"), dict) else {}
    manifest = capabilities.get("integration_manifest") if isinstance(capabilities.get("integration_manifest"), dict) else {}
    deployment_profile = (
        capabilities.get("deployment_profile") if isinstance(capabilities.get("deployment_profile"), dict) else {}
    )
    selection_policy = capabilities.get("selection_policy") if isinstance(capabilities.get("selection_policy"), dict) else {}
    provider_readiness = get_mailbox_provider_readiness_summary(
        provider_diagnostics=(
            capabilities.get("provider_diagnostics") if isinstance(capabilities.get("provider_diagnostics"), dict) else {}
        ),
        provider_integration_guide=(
            capabilities.get("provider_integration_guide")
            if isinstance(capabilities.get("provider_integration_guide"), dict)
            else {}
        ),
        selection_policy=selection_policy,
        discovery={
            "providers_endpoint": endpoints.get("providers") or _CANONICAL_EXTERNAL_ENDPOINTS["providers"],
            "provider_health_endpoint": endpoints.get("provider_health") or PROVIDER_HEALTH_ENDPOINT,
            "provider_preflight_endpoint": endpoints.get("provider_preflight") or PROVIDER_PREFLIGHT_ENDPOINT,
        },
    )
    readiness = get_external_api_readiness_summary(
        consumer=consumer,
        database_ok=database_ok,
        upstream_probe_ok=upstream_probe_ok,
    )
    status = _integration_bundle_status(readiness, provider_readiness)
    smoke_checks = _integration_bundle_smoke_checks(endpoints)
    recommendations = _integration_bundle_recommendations(
        status=status,
        endpoints=endpoints,
        readiness=readiness,
        provider_readiness=provider_readiness,
    )
    action_plan = _integration_bundle_action_plan(
        status=status,
        endpoints=endpoints,
        readiness=readiness,
        provider_readiness=provider_readiness,
        smoke_checks=smoke_checks,
        recommendations=recommendations,
        quickstart=capabilities.get("quickstart") if isinstance(capabilities.get("quickstart"), dict) else {},
    )
    return {
        "version": 1,
        "service": str(service or "mailops"),
        "app_version": str(version or ""),
        "status": status,
        "generated_at": _external_bundle_now(),
        "auth": _integration_bundle_auth(manifest),
        "endpoints": copy.deepcopy(endpoints),
        "legacy_endpoints": copy.deepcopy(capabilities.get("legacy_endpoints") or {}),
        "compatibility": copy.deepcopy(capabilities.get("compatibility") or {}),
        "documentation": copy.deepcopy(capabilities.get("documentation") or {}),
        "quickstart": copy.deepcopy(capabilities.get("quickstart") or {}),
        "readiness": {
            "status": status,
            "external_api": copy.deepcopy(readiness),
            "providers": provider_readiness,
            "mailbox_directory": copy.deepcopy(readiness.get("mailbox_directory") or {}),
            "pool": copy.deepcopy(readiness.get("pool") or {}),
            "task_temp_mailbox": copy.deepcopy(readiness.get("task_temp_mailbox") or {}),
            "warnings": list(readiness.get("warnings") or []),
        },
        "provider_selection": _integration_bundle_provider_selection(
            capabilities=capabilities,
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_readiness=provider_readiness,
        ),
        "openapi": _integration_bundle_openapi(openapi_metadata, endpoints=endpoints),
        "workflows": _integration_bundle_workflows(manifest),
        "smoke_checks": smoke_checks,
        "recommendations": recommendations,
        "action_plan": action_plan,
    }


def _external_bundle_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _integration_bundle_auth(manifest: dict[str, Any]) -> dict[str, str]:
    auth = manifest.get("auth") if isinstance(manifest.get("auth"), dict) else {}
    return {
        "header": str(auth.get("header") or "X-API-Key"),
        "placeholder": str(auth.get("placeholder") or "<your-api-key>"),
    }


def _integration_bundle_status(readiness: dict[str, Any], provider_readiness: dict[str, Any]) -> str:
    provider_status = str(provider_readiness.get("overall_status") or "").strip().lower()
    external_status = str(readiness.get("status") or "").strip().lower()
    if provider_status == "degraded" or external_status == "degraded":
        return "degraded"
    if provider_status == "needs_config":
        return "needs_config"
    return "ready"


def _integration_bundle_provider_selection(
    *,
    capabilities: dict[str, Any],
    deployment_profile: dict[str, Any],
    selection_policy: dict[str, Any],
    provider_readiness: dict[str, Any],
) -> dict[str, Any]:
    defaults = capabilities.get("defaults") if isinstance(capabilities.get("defaults"), dict) else {}
    if isinstance(capabilities.get("cors"), dict):
        cors_contract = capabilities["cors"]
    return {
        "source_priority": list(selection_policy.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY),
        "selector_fields": copy.deepcopy(provider_readiness.get("provider_selector_fields") or {}),
        "provider_values": copy.deepcopy(deployment_profile.get("provider_values") or {}),
        "defaults": {
            "pool_claim_provider": str(defaults.get("pool_claim_provider") or "auto"),
            "temp_mail_provider": str(defaults.get("temp_mail_provider") or ""),
            "active_mailbox_providers": list(defaults.get("active_mailbox_providers") or []),
        },
        "config_file": copy.deepcopy(selection_policy.get("config_file") or deployment_profile.get("config_file") or {}),
        "selection_recipes_count": len(selection_policy.get("selection_recipes") or []),
        "routing_matrix": copy.deepcopy(provider_readiness.get("routing_matrix") or {}),
    }


def _integration_bundle_openapi(openapi_metadata: dict[str, Any] | None, *, endpoints: dict[str, Any]) -> dict[str, Any]:
    metadata = openapi_metadata if isinstance(openapi_metadata, dict) else {}
    paths = metadata.get("paths") if isinstance(metadata.get("paths"), dict) else {}
    schemas = ((metadata.get("components") or {}).get("schemas") or {}) if isinstance(metadata.get("components"), dict) else {}
    return {
        "endpoint": str(endpoints.get("openapi") or _CANONICAL_EXTERNAL_ENDPOINTS["openapi"]),
        "version": str(metadata.get("openapi") or ""),
        "path_count": len(paths),
        "schema_count": len(schemas) if isinstance(schemas, dict) else 0,
        "operation_count": _integration_bundle_operation_count(paths),
    }


def _integration_bundle_operation_count(paths: dict[str, Any]) -> int:
    count = 0
    for methods in paths.values():
        if not isinstance(methods, dict):
            continue
        count += sum(1 for method in methods if str(method).lower() in {"get", "post", "put", "patch", "delete"})
    return count


def _integration_bundle_workflows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    workflows = manifest.get("workflows") if isinstance(manifest.get("workflows"), list) else []
    rows: list[dict[str, Any]] = []
    for workflow in workflows:
        if not isinstance(workflow, dict) or not workflow.get("key"):
            continue
        steps = workflow.get("steps") if isinstance(workflow.get("steps"), list) else []
        rows.append(
            {
                "key": str(workflow.get("key")),
                "label": str(workflow.get("label") or workflow.get("key")),
                "description": str(workflow.get("description") or ""),
                "step_count": len(steps),
            }
        )
    return rows


def _integration_bundle_smoke_checks(endpoints: dict[str, Any]) -> list[dict[str, str]]:
    checks = [
        ("health", "GET", endpoints.get("health"), "Confirm API key auth, database, and readiness status."),
        ("capabilities", "GET", endpoints.get("capabilities"), "Read the canonical capability and endpoint map."),
        (
            "integration_bundle",
            "GET",
            endpoints.get("integration_bundle"),
            "Fetch this one-stop integration readiness bundle.",
        ),
        ("providers", "GET", endpoints.get("providers"), "Inspect provider readiness and selection metadata."),
        ("mailboxes", "GET", endpoints.get("mailboxes"), "Probe the unified mailbox directory with page_size=1."),
        ("openapi", "GET", endpoints.get("openapi"), "Load the generated OpenAPI contract."),
    ]
    return [
        {
            "key": key,
            "method": method,
            "endpoint": str(endpoint),
            "purpose": purpose,
        }
        for key, method, endpoint, purpose in checks
        if endpoint
    ]


def _integration_bundle_recommendations(
    *,
    status: str,
    endpoints: dict[str, Any],
    readiness: dict[str, Any],
    provider_readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    warnings = {str(item) for item in (readiness.get("warnings") or [])}
    issues = provider_readiness.get("issues") if isinstance(provider_readiness.get("issues"), dict) else {}
    recommendations: list[dict[str, Any]] = []
    if status == "ready":
        recommendations.append(
            {
                "key": "start_mailbox_session",
                "priority": "high",
                "label": "Start with provider-neutral mailbox sessions",
                "endpoint": str(
                    endpoints.get("mailbox_session_start") or _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_start"]
                ),
            }
        )
    if "provider_config_required" in warnings or int(issues.get("needs_config") or 0) > 0:
        recommendations.append(
            {
                "key": "configure_providers",
                "priority": "high",
                "label": "Configure providers with missing local settings before relying on automatic source selection",
                "endpoint": str(endpoints.get("providers") or _CANONICAL_EXTERNAL_ENDPOINTS["providers"]),
            }
        )
    if "pool_access_required" in warnings:
        recommendations.append(
            {
                "key": "pool_access",
                "priority": "medium",
                "label": "Use task_temp_only sessions or issue a scoped API key with pool access",
                "endpoint": str(
                    endpoints.get("mailbox_session_start") or _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_start"]
                ),
            }
        )
    if "external_pool_disabled" in warnings:
        recommendations.append(
            {
                "key": "enable_external_pool",
                "priority": "medium",
                "label": "Enable the external mailbox pool when reusable account inventory should be claimable",
                "endpoint": str(endpoints.get("pool_claim_random") or _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_random"]),
            }
        )
    mailbox_status = str((readiness.get("mailbox_directory") or {}).get("status") or "")
    if mailbox_status in {"empty", "restricted"}:
        recommendations.append(
            {
                "key": "probe_mailbox_directory",
                "priority": "medium",
                "label": "Probe the unified mailbox directory and confirm the API key email scope",
                "endpoint": str(endpoints.get("mailboxes") or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
            }
        )
    recommendations.append(
        {
            "key": "generate_client",
            "priority": "low",
            "label": "Generate or update external clients from the canonical OpenAPI contract",
            "endpoint": str(endpoints.get("openapi") or _CANONICAL_EXTERNAL_ENDPOINTS["openapi"]),
        }
    )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in recommendations:
        key = str(item.get("key") or "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _integration_bundle_action_plan(
    *,
    status: str,
    endpoints: dict[str, Any],
    readiness: dict[str, Any],
    provider_readiness: dict[str, Any],
    smoke_checks: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    quickstart: dict[str, Any],
) -> dict[str, Any]:
    warnings = {str(item) for item in (readiness.get("warnings") or [])}
    issues = provider_readiness.get("issues") if isinstance(provider_readiness.get("issues"), dict) else {}
    mailbox_directory = readiness.get("mailbox_directory") if isinstance(readiness.get("mailbox_directory"), dict) else {}
    pool = readiness.get("pool") if isinstance(readiness.get("pool"), dict) else {}
    recommendation_keys = {str(item.get("key") or "") for item in recommendations if isinstance(item, dict)}
    smoke_keys = {str(item.get("key") or "") for item in smoke_checks if isinstance(item, dict)}
    items: list[dict[str, Any]] = []

    def endpoint(name: str) -> str:
        return str(endpoints.get(name) or _CANONICAL_EXTERNAL_ENDPOINTS.get(name) or "")

    def quickstart_endpoint(request_key: str, fallback_name: str) -> str:
        requests = quickstart.get("requests") if isinstance(quickstart.get("requests"), dict) else {}
        request = requests.get(request_key) if isinstance(requests.get(request_key), dict) else {}
        return str(request.get("endpoint") or endpoint(fallback_name))

    def add(item: dict[str, Any]) -> None:
        key = str(item.get("key") or "").strip()
        if not key:
            return
        item["key"] = key
        item["priority"] = str(item.get("priority") or "medium")
        item["status"] = str(item.get("status") or "optional")
        item["blocking"] = bool(item.get("blocking"))
        items.append(item)

    provider_needs_config = "provider_config_required" in warnings or int(issues.get("needs_config") or 0) > 0
    if provider_needs_config or "configure_providers" in recommendation_keys:
        add(
            {
                "key": "configure_providers",
                "priority": "high",
                "status": "action_required",
                "blocking": status in {"needs_config", "degraded"},
                "title": "Configure providers with missing local settings",
                "detail": "Fix provider readiness before relying on automatic mailbox source selection.",
                "endpoint": endpoint("providers"),
                "docs": "docs/provider-onboarding.md",
            }
        )

    pool_status = str(pool.get("status") or "").strip().lower()
    pool_restrictions = {str(item) for item in (pool.get("restrictions") or [])}
    if "pool_access_required" in warnings or "pool_access_required" in pool_restrictions or pool_status == "restricted":
        add(
            {
                "key": "use_task_temp_only_or_pool_key",
                "priority": "high",
                "status": "action_required",
                "blocking": status in {"needs_config", "degraded"},
                "title": "Use task_temp_only or issue a pool-enabled API key",
                "detail": "The current API key cannot claim reusable pool inventory; use task temp mailboxes or a scoped key with pool access.",
                "endpoint": quickstart_endpoint("mailbox_session_start", "mailbox_session_start"),
                "docs": "docs/external-integration-quickstart.md",
            }
        )

    if "external_pool_disabled" in warnings or "external_pool_disabled" in pool_restrictions or pool_status == "disabled":
        add(
            {
                "key": "enable_external_pool",
                "priority": "medium",
                "status": "action_required" if status in {"needs_config", "degraded"} else "optional",
                "blocking": False,
                "title": "Enable the external mailbox pool when reusable inventory is required",
                "detail": "Pool endpoints are disabled; task temp mailbox sessions can still be used when available.",
                "endpoint": endpoint("pool_claim_random"),
                "docs": "docs/external-integration-quickstart.md",
            }
        )

    mailbox_status = str(mailbox_directory.get("status") or "").strip().lower()
    if mailbox_status in {"empty", "restricted", "degraded"}:
        add(
            {
                "key": "probe_mailbox_directory",
                "priority": "medium",
                "status": "action_required" if mailbox_status in {"restricted", "degraded"} else "optional",
                "blocking": mailbox_status == "degraded" and status == "degraded",
                "title": "Probe the unified mailbox directory",
                "detail": "Confirm the current API key scope and visible Outlook, IMAP, pool, and temp-mail inventory before selecting a source.",
                "endpoint": endpoint("mailboxes"),
                "docs": "docs/external-integration-quickstart.md",
            }
        )

    add(
        {
            "key": "run_smoke_check",
            "priority": "high",
            "status": "ready" if "integration_bundle" in smoke_keys else "action_required",
            "blocking": False,
            "title": "Run the read-only smoke check",
            "detail": "Validate discovery, OpenAPI, provider readiness, mailbox directory, and secret safety before mutating mailbox state.",
            "endpoint": endpoint("integration_bundle"),
            "command": "MAILOPS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
            "docs": "docs/external-integration-quickstart.md",
        }
    )
    add(
        {
            "key": "generate_client",
            "priority": "medium" if "generate_client" in recommendation_keys else "low",
            "status": "ready",
            "blocking": False,
            "title": "Generate or refresh the external client",
            "detail": "Use the canonical OpenAPI document after the smoke check passes.",
            "endpoint": endpoint("openapi"),
            "docs": "docs/external-integration-quickstart.md",
        }
    )
    add(
        {
            "key": "start_mailbox_session",
            "priority": "high",
            "status": "ready" if status == "ready" else "blocked",
            "blocking": False,
            "title": "Start a provider-neutral mailbox session",
            "detail": "Use mailbox sessions as the stable abstraction over pool claims and task temp-mail providers.",
            "endpoint": quickstart_endpoint("mailbox_session_start", "mailbox_session_start"),
            "docs": "docs/external-integration-quickstart.md",
        }
    )

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("key") or "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    summary = {
        "total": len(deduped),
        "blocking": sum(1 for item in deduped if item.get("blocking") is True),
        "high": sum(1 for item in deduped if item.get("priority") == "high"),
        "medium": sum(1 for item in deduped if item.get("priority") == "medium"),
        "low": sum(1 for item in deduped if item.get("priority") == "low"),
    }
    return {
        "version": 1,
        "status": status if status in {"ready", "needs_config", "degraded"} else "degraded",
        "summary": summary,
        "items": deduped,
    }
