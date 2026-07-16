from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from outlook_web import __version__ as APP_VERSION
from outlook_web.repositories import settings as settings_repo
from outlook_web.services.external_api_openapi import get_external_api_openapi_contract
from outlook_web.services.mailbox_catalog import list_unified_mailboxes
from outlook_web.services.provider_catalog import (
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    get_active_mailbox_provider_filter_contract,
    get_external_api_capabilities_contract,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_api_integration_bundle,
    get_external_api_readiness_summary,
    get_external_integration_manifest,
    get_external_mailbox_read_contract,
    get_mailbox_provider_catalog,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_mailbox_provider_readiness_summary,
    get_mailbox_provider_selection_policy,
    get_operator_temp_mail_default_provider,
    get_provider_alias_contract,
    get_provider_documentation_contract,
    get_provider_integration_guide,
    temp_mail_provider_config_status,
)
from scripts.external_api_smoke import SECRET_PATTERNS, CheckResult, validate_contracts

GROUP_LABELS = {
    "health": "Health readiness",
    "capabilities": "Capabilities",
    "integration_bundle": "Integration bundle",
    "quickstart": "Quickstart",
    "manifest": "Integration manifest",
    "endpoints": "Canonical endpoints",
    "legacy_endpoints": "Legacy compatibility",
    "compatibility": "Compatibility metadata",
    "mailbox_session": "Mailbox sessions",
    "documentation": "Documentation",
    "openapi": "OpenAPI",
    "providers": "Provider readiness",
    "mailboxes": "Mailbox directory",
    "secret_scan": "Secret safety",
    "local_safety": "Local safety posture",
}

CRITICAL_PREFIXES = (
    "secret_scan",
    "health.readiness",
    "integration_bundle",
    "manifest.auth",
    "manifest.workflows",
    "endpoints.",
    "openapi.path",
    "openapi.schema",
    "providers.readiness",
    "mailboxes.readiness",
    "providers.routing_matrix",
    "mailboxes.routing_matrix",
)


def get_external_api_contract_check() -> dict[str, Any]:
    """Return a secret-safe local validation report for external API discovery."""

    try:
        payloads = _build_local_contract_payloads()
        results = validate_contracts(
            health_payload=payloads["health"],
            capabilities_payload=payloads["capabilities"],
            integration_bundle_payload=payloads["integration_bundle"],
            providers_payload=payloads["providers"],
            mailboxes_payload=payloads["mailboxes"],
            openapi_payload=payloads["openapi"],
        )
        results.extend(_local_safety_checks(payloads))
        return _build_report(results)
    except Exception as exc:
        return _build_error_report(exc)


def _build_local_contract_payloads() -> dict[str, dict[str, Any]]:
    readiness = get_external_api_readiness_summary(consumer=None, database_ok=True, upstream_probe_ok=None)
    health_data = {
        "status": "ok",
        "service": "outlook-email-plus",
        "version": APP_VERSION,
        "server_time_utc": _utc_now(),
        "database": "ok",
        "upstream_probe_ok": None,
        "last_probe_at": "",
        "last_probe_error": "",
        "readiness": readiness,
    }
    capabilities = {
        "service": "outlook-email-plus",
        "version": APP_VERSION,
        **get_external_api_capabilities_contract(consumer=None),
    }
    openapi = get_external_api_openapi_contract(consumer=None)
    integration_bundle = get_external_api_integration_bundle(
        consumer=None,
        service="outlook-email-plus",
        version=APP_VERSION,
        database_ok=True,
        upstream_probe_ok=None,
        openapi_metadata=openapi,
    )
    providers = _get_local_provider_discovery_payload()
    mailboxes = list_unified_mailboxes(page=1, page_size=1)
    return {
        "health": _ok_envelope(health_data),
        "capabilities": _ok_envelope(capabilities),
        "integration_bundle": _ok_envelope(integration_bundle),
        "providers": _ok_envelope(providers),
        "mailboxes": _ok_envelope(mailboxes),
        "openapi": openapi,
    }


def _get_local_provider_discovery_payload() -> dict[str, Any]:
    endpoints = get_external_api_endpoint_map()
    provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
    provider_diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
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
    default_provider = get_operator_temp_mail_default_provider(strict=False)
    default_provider_config = temp_mail_provider_config_status(default_provider)
    return {
        "mailbox_providers": get_mailbox_provider_catalog(strict=False),
        "provider_diagnostics": provider_diagnostics,
        "provider_filter": provider_filter,
        "active_mailbox_providers": provider_filter["active_providers"],
        "default_temp_mail_provider": default_provider,
        "default_temp_mail_provider_configured": bool(default_provider_config.get("configured")),
        "default_temp_mail_provider_missing_config": list(default_provider_config.get("missing_config") or []),
        "default_pool_claim_provider": settings_repo.get_pool_default_provider(strict=False) or "auto",
        "deployment_profile": deployment_profile,
        "selection_policy": selection_policy,
        "provider_integration_guide": integration_guide,
        "readiness_summary": readiness_summary,
        "integration_manifest": integration_manifest,
        "quickstart": dict(integration_manifest.get("quickstart") or {}),
        "compatibility": compatibility,
        "legacy_endpoints": dict(compatibility.get("legacy_endpoints") or {}),
        "documentation": get_provider_documentation_contract(),
        "endpoints": endpoints,
        "provider_health_endpoint": PROVIDER_HEALTH_ENDPOINT,
        "provider_preflight_endpoint": PROVIDER_PREFLIGHT_ENDPOINT,
        **get_provider_alias_contract(),
        "external_mailbox_read_contract": get_external_mailbox_read_contract(lifecycle="none"),
    }


def _local_safety_checks(payloads: dict[str, dict[str, Any]]) -> list[CheckResult]:
    serialized = json.dumps(payloads, ensure_ascii=False, sort_keys=True)
    secret_hits = [pattern.pattern for pattern in SECRET_PATTERNS if pattern.search(serialized)]
    return [
        CheckResult(True, "local_safety.local_only", "contract check runs in-process without HTTP calls"),
        CheckResult(True, "local_safety.network_probes", "contract check does not probe upstream providers"),
        CheckResult(True, "local_safety.mutation_safe", "contract check does not create, claim, read, or mutate mailboxes"),
        CheckResult(
            not secret_hits, "local_safety.secret_patterns", "contract check payloads do not contain obvious secret values"
        ),
    ]


def _build_report(results: list[CheckResult]) -> dict[str, Any]:
    check_rows = [_check_row(result) for result in results]
    groups = _group_checks(check_rows)
    failed = [row for row in check_rows if not row["passed"]]
    critical = [row for row in failed if row["severity"] == "critical"]
    warning = [row for row in failed if row["severity"] == "warning"]
    return {
        "version": 1,
        "status": "fail" if failed else "pass",
        "generated_at": _utc_now(),
        "local_only": True,
        "network_probes": False,
        "mutation_safe": True,
        "summary": {
            "total": len(check_rows),
            "passed": len(check_rows) - len(failed),
            "failed": len(failed),
            "warnings": len(warning),
            "critical": len(critical),
            "groups": len(groups),
        },
        "groups": groups,
        "next_actions": _next_actions(failed),
    }


def _build_error_report(exc: Exception) -> dict[str, Any]:
    safe_type = type(exc).__name__
    return {
        "version": 1,
        "status": "error",
        "generated_at": _utc_now(),
        "local_only": True,
        "network_probes": False,
        "mutation_safe": True,
        "summary": {"total": 0, "passed": 0, "failed": 1, "warnings": 0, "critical": 1, "groups": 1},
        "groups": [
            {
                "key": "contract_check",
                "label": "Contract check",
                "status": "error",
                "summary": {"total": 1, "passed": 0, "failed": 1},
                "checks": [
                    {
                        "name": "contract_check.error",
                        "description": "Local contract check could not complete",
                        "passed": False,
                        "group": "contract_check",
                        "severity": "critical",
                        "detail": safe_type,
                    }
                ],
            }
        ],
        "next_actions": [
            {
                "key": "inspect_server_logs",
                "priority": "high",
                "label": "Inspect server logs for the contract-check exception type",
                "target": safe_type,
            }
        ],
    }


def _check_row(result: CheckResult) -> dict[str, Any]:
    group = _group_key(result.name)
    return {
        "name": result.name,
        "description": result.message,
        "passed": bool(result.ok),
        "group": group,
        "severity": "info" if result.ok else _severity(result.name),
    }


def _group_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in checks:
        grouped.setdefault(str(row["group"]), []).append(row)
    groups: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        failed = [row for row in rows if not row["passed"]]
        groups.append(
            {
                "key": key,
                "label": GROUP_LABELS.get(key, key.replace("_", " ").title()),
                "status": "fail" if failed else "pass",
                "summary": {"total": len(rows), "passed": len(rows) - len(failed), "failed": len(failed)},
                "checks": rows[:20],
            }
        )
    return groups


def _next_actions(failed: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not failed:
        return [
            {
                "key": "run_external_smoke",
                "priority": "low",
                "label": "Run the live read-only smoke check from the target deployment",
                "target": "OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
            }
        ]
    actions = []
    group_keys = {str(item.get("group") or "") for item in failed}
    if "providers" in group_keys or "mailboxes" in group_keys:
        actions.append(
            {
                "key": "inspect_provider_preflight",
                "priority": "high",
                "label": "Inspect provider preflight",
                "target": "/api/providers/preflight",
            }
        )
    if "openapi" in group_keys or "endpoints" in group_keys or "compatibility" in group_keys:
        actions.append(
            {
                "key": "inspect_openapi",
                "priority": "high",
                "label": "Inspect OpenAPI and endpoint maps",
                "target": "/api/v1/external/openapi.json",
            }
        )
    actions.append(
        {
            "key": "inspect_integration_bundle",
            "priority": "medium",
            "label": "Inspect the integration bundle action plan",
            "target": "/api/v1/external/integration-bundle",
        }
    )
    return actions[:4]


def _severity(name: str) -> str:
    return "critical" if name.startswith(CRITICAL_PREFIXES) else "warning"


def _group_key(name: str) -> str:
    if name.startswith("legacy_endpoints."):
        return "legacy_endpoints"
    if name.startswith("openapi.x_legacy_endpoints"):
        return "legacy_endpoints"
    if name.startswith("compatibility."):
        return "compatibility"
    if name.startswith("mailbox_session."):
        return "mailbox_session"
    if name.startswith("manifest."):
        return "manifest"
    if name.startswith("quickstart."):
        return "quickstart"
    if name.startswith("documentation."):
        return "documentation"
    if name.startswith("secret_scan."):
        return "secret_scan"
    if name.startswith("local_safety."):
        return "local_safety"
    if "." in name:
        return name.split(".", 1)[0]
    return name


def _ok_envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "code": "OK", "message": "ok", "data": data}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
