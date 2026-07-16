from __future__ import annotations

import copy
from typing import Any

from flask import jsonify, request

from outlook_web.repositories import settings as settings_repo
from outlook_web.security.auth import api_key_required, get_external_api_consumer
from outlook_web.security.external_api_guard import check_feature_enabled, external_api_guards
from outlook_web.services import external_api as external_api_service
from outlook_web.services.external_request_limits import CALLER_ID_MAX_LEN, DETAIL_MAX_LEN, TASK_ID_MAX_LEN
from outlook_web.services.mailbox_catalog import MailboxCatalogError, list_unified_mailboxes
from outlook_web.services.pool import PoolServiceError, claim_random, complete_claim, release_claim
from outlook_web.services.provider_catalog import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    MAILBOX_SESSION_CLOSE_ENDPOINT,
    MAILBOX_SESSION_READ_ENDPOINT,
    MAILBOX_SESSION_START_ENDPOINT,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    TEMP_MAIL_PROVIDER_ENV,
    get_active_mailbox_provider_filter_contract,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_integration_manifest,
    get_external_mailbox_read_contract,
    get_mailbox_provider_catalog,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_mailbox_provider_health,
    get_mailbox_provider_preflight,
    get_mailbox_provider_readiness_summary,
    get_mailbox_provider_selection_policy,
    get_operator_temp_mail_default_provider,
    get_provider_alias_contract,
    get_provider_documentation_contract,
    get_provider_integration_guide,
    mailbox_session_provider_metadata,
    temp_mail_provider_config_status,
    temp_mail_provider_label,
)
from outlook_web.services.temp_mail_service import TempMailError, get_temp_mail_service

from .helpers import _audit


@api_key_required
@external_api_guards()
def api_external_list_mailboxes():
    endpoint = "/api/v1/external/mailboxes"
    consumer = get_external_api_consumer() or {}
    allowed_account_emails = [str(item or "").strip() for item in (consumer.get("allowed_emails") or [])]
    try:
        payload = list_unified_mailboxes(
            kind=request.args.get("kind", "all"),
            status=request.args.get("status", "all"),
            read_capability=request.args.get("read_capability", "all"),
            action=request.args.get("action", "all"),
            provider=request.args.get("provider", "all"),
            search=request.args.get("search", ""),
            sort=request.args.get("sort", "updated_desc"),
            page=request.args.get("page", 1),
            page_size=request.args.get("page_size", 50),
            allowed_account_emails=allowed_account_emails,
        )
        _audit(
            endpoint,
            "ok",
            details={
                "count": payload.get("pagination", {}).get("total_count", 0),
                "kind": payload.get("filters", {}).get("kind", "all"),
                "read_capability": payload.get("filters", {}).get("read_capability", "all"),
                "action": payload.get("filters", {}).get("action", "all"),
                "provider": payload.get("filters", {}).get("provider", "all"),
                "sort": payload.get("filters", {}).get("sort", "updated_desc"),
            },
            email_addr="",
        )
        return jsonify(external_api_service.ok(payload))
    except MailboxCatalogError as exc:
        _audit(endpoint, "error", details={"code": exc.code, **(exc.data or {})}, email_addr="")
        return jsonify(external_api_service.fail(exc.code, exc.message, data=exc.data)), 400
    except Exception as exc:
        _audit(endpoint, "error", details={"code": "INTERNAL_ERROR", "err": type(exc).__name__}, email_addr="")
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_get_providers():
    endpoint = "/api/v1/external/providers"
    endpoints = get_external_api_endpoint_map()
    # Operator/API default must match collapsed guide/diagnostics bridge key.
    default_provider = get_operator_temp_mail_default_provider(strict=False)
    default_pool_provider = settings_repo.get_pool_default_provider(strict=False)
    default_provider_config = temp_mail_provider_config_status(default_provider)
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
    integration_manifest = get_external_integration_manifest(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=provider_diagnostics,
        provider_integration_guide=integration_guide,
    )
    readiness_summary = get_mailbox_provider_readiness_summary(
        provider_diagnostics=provider_diagnostics,
        provider_integration_guide=integration_guide,
        selection_policy=selection_policy,
        discovery={
            "providers_endpoint": endpoints["providers"],
            "provider_health_endpoint": PROVIDER_HEALTH_ENDPOINT,
            "provider_preflight_endpoint": PROVIDER_PREFLIGHT_ENDPOINT,
        },
    )
    compatibility = get_external_api_compatibility_contract()
    payload = {
        "mailbox_providers": get_mailbox_provider_catalog(strict=False),
        "provider_diagnostics": provider_diagnostics,
        "provider_filter": provider_filter,
        "active_mailbox_providers": provider_filter["active_providers"],
        "active_mailbox_provider_env": ACTIVE_MAILBOX_PROVIDER_ENV,
        "default_temp_mail_provider": default_provider,
        "default_temp_mail_provider_label": temp_mail_provider_label(default_provider),
        "default_temp_mail_provider_configured": bool(default_provider_config["configured"]),
        "default_temp_mail_provider_missing_config": list(default_provider_config["missing_config"]),
        "default_pool_claim_provider": default_pool_provider or "auto",
        "default_pool_claim_provider_env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
        "supports_temp_mail_provider_selection": True,
        "runtime_temp_mail_provider_env": TEMP_MAIL_PROVIDER_ENV,
        "deployment_env": dict(DEPLOYMENT_ENV_CONTRACT),
        "deployment_profile": deployment_profile,
        "selection_policy": selection_policy,
        "provider_integration_guide": integration_guide,
        "readiness_summary": readiness_summary,
        "integration_manifest": integration_manifest,
        "quickstart": copy.deepcopy(integration_manifest.get("quickstart") or {}),
        "compatibility": compatibility,
        "legacy_endpoints": copy.deepcopy(compatibility["legacy_endpoints"]),
        "documentation": get_provider_documentation_contract(),
        "endpoints": endpoints,
        "pool_claim_endpoint": endpoints["pool_claim_random"],
        "pool_claim_fields": ["caller_id", "task_id", "provider", "email_domain", "project_key"],
        "provider_health_endpoint": PROVIDER_HEALTH_ENDPOINT,
        "provider_health_fields": ["kind", "provider", "probe_network"],
        "provider_preflight_endpoint": PROVIDER_PREFLIGHT_ENDPOINT,
        "provider_preflight_fields": ["probe_network"],
        **get_provider_alias_contract(),
        "external_mailbox_read_contract": get_external_mailbox_read_contract(lifecycle="none"),
        "temp_mail_apply_endpoint": endpoints["temp_mail_apply"],
        "temp_mail_apply_fields": ["caller_id", "task_id", "prefix", "domain", "provider_name"],
    }
    _audit(endpoint, "ok", details={"default_temp_mail_provider": default_provider}, email_addr="")
    return jsonify(external_api_service.ok(payload))


@api_key_required
@external_api_guards()
def api_external_get_provider_preflight():
    endpoint = PROVIDER_PREFLIGHT_ENDPOINT
    probe_network = str(request.args.get("probe_network") or "").strip().lower() in {"1", "true", "yes", "on"}
    payload = get_mailbox_provider_preflight(probe_network=probe_network)
    _audit(
        endpoint,
        "ok",
        details={
            "status": payload.get("status"),
            "network_probe": bool((payload.get("scope") or {}).get("network_probe")),
            "provider_total": (payload.get("summary") or {}).get("total"),
            "probe_failed": (payload.get("summary") or {}).get("probe_failed"),
        },
        email_addr="",
    )
    return jsonify(external_api_service.ok(payload))


@api_key_required
@external_api_guards()
def api_external_get_provider_health(kind: str, provider: str):
    endpoint = PROVIDER_HEALTH_ENDPOINT
    probe_network = str(request.args.get("probe_network") or "").strip().lower() in {"1", "true", "yes", "on"}
    payload = get_mailbox_provider_health(kind, provider, probe_network=probe_network)
    if not payload.get("found"):
        _audit(
            endpoint,
            "error",
            details={"code": "MAILBOX_PROVIDER_NOT_FOUND", "kind": kind, "provider": provider},
            email_addr="",
        )
        return (
            jsonify(
                external_api_service.fail(
                    "MAILBOX_PROVIDER_NOT_FOUND",
                    "邮箱 Provider 不存在",
                    data={"kind": kind, "provider": provider},
                )
            ),
            404,
        )
    _audit(
        endpoint,
        "ok",
        details={
            "kind": payload.get("kind"),
            "provider": payload.get("provider"),
            "local_status": payload.get("local_status"),
            "probe_status": (payload.get("probe") or {}).get("status"),
            "network_probe": (payload.get("probe") or {}).get("network_probe"),
        },
        email_addr="",
    )
    return jsonify(external_api_service.ok(payload))
