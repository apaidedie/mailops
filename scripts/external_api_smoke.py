from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


EXPECTED_STRATEGIES = ["pool_first", "task_temp_first", "pool_only", "task_temp_only"]
CANONICAL_EXTERNAL_PREFIX = "/api/v1/external"
LEGACY_EXTERNAL_PREFIX = "/api/external"
CANONICAL_HEALTH = f"{CANONICAL_EXTERNAL_PREFIX}/health"
CANONICAL_CAPABILITIES = f"{CANONICAL_EXTERNAL_PREFIX}/capabilities"
CANONICAL_INTEGRATION_BUNDLE = f"{CANONICAL_EXTERNAL_PREFIX}/integration-bundle"
CANONICAL_DOCS = f"{CANONICAL_EXTERNAL_PREFIX}/docs"
CANONICAL_OPENAPI = f"{CANONICAL_EXTERNAL_PREFIX}/openapi.json"
CANONICAL_PROVIDERS = f"{CANONICAL_EXTERNAL_PREFIX}/providers"
CANONICAL_PROVIDER_PREFLIGHT = f"{CANONICAL_EXTERNAL_PREFIX}/providers/preflight"
CANONICAL_MAILBOXES = f"{CANONICAL_EXTERNAL_PREFIX}/mailboxes"
CANONICAL_SESSION_START = f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start"
CANONICAL_SESSION_CLOSE = f"{CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close"
LEGACY_DOCS = f"{LEGACY_EXTERNAL_PREFIX}/docs"
LEGACY_INTEGRATION_BUNDLE = f"{LEGACY_EXTERNAL_PREFIX}/integration-bundle"
LEGACY_PROVIDER_PREFLIGHT = f"{LEGACY_EXTERNAL_PREFIX}/providers/preflight"
LEGACY_SESSION_START = f"{LEGACY_EXTERNAL_PREFIX}/mailbox-sessions/start"
LEGACY_SESSION_CLOSE = f"{LEGACY_EXTERNAL_PREFIX}/mailbox-sessions/close"
REQUIRED_HEALTH_READINESS_SECTIONS = {
    "status",
    "database",
    "upstream_probe",
    "discovery",
    "providers",
    "mailbox_directory",
    "pool",
    "task_temp_mailbox",
    "warnings",
}
REQUIRED_HEALTH_DISCOVERY_ENDPOINTS = {
    "capabilities": CANONICAL_CAPABILITIES,
    "integration_bundle": CANONICAL_INTEGRATION_BUNDLE,
    "docs": CANONICAL_DOCS,
    "providers": CANONICAL_PROVIDERS,
    "mailboxes": CANONICAL_MAILBOXES,
    "openapi": CANONICAL_OPENAPI,
}
REQUIRED_PROVIDER_SUMMARY_FIELDS = {
    "total",
    "active",
    "ready",
    "needs_config",
    "dynamic_create",
    "account",
    "temp",
    "unknown_filter_entries",
    "invalid_default_entries",
    "inactive_default_entries",
}
REQUIRED_PROVIDER_READINESS_TOTALS = {
    "mailboxes",
    "account_mailboxes",
    "temp_mailboxes",
    "providers",
    "active_providers",
    "ready_providers",
    "configured_providers",
    "needs_config_providers",
    "dynamic_create_providers",
    "account_providers",
    "temp_providers",
}
REQUIRED_PROVIDER_READINESS_ISSUES = {
    "needs_config",
    "inactive",
    "unknown_filter_entries",
    "invalid_default_entries",
    "inactive_default_entries",
}
REQUIRED_PROVIDER_SELECTOR_FIELDS = {
    "pool_claim": "provider",
    "task_temp_apply": "provider_name",
}
REQUIRED_ROUTING_SCOPES = {
    "temp_runtime_default",
    "task_temp_apply",
    "pool_claim_default",
    "explicit_pool_claim",
}
REQUIRED_WORKFLOWS = {
    "start_mailbox_session",
    "browse_mailbox_directory",
    "claim_pool_mailbox",
    "create_task_temp_mailbox",
}
ACTION_PLAN_PRIORITIES = {"high", "medium", "low"}
ACTION_PLAN_STATUSES = {"ready", "action_required", "optional", "blocked"}
SECRET_PATTERNS = [
    re.compile(r"dk_[0-9a-fA-F]{40,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_.-]{20,}", re.IGNORECASE),
    re.compile(r"X-API-Key:\s+(?!<your-api-key>)[A-Za-z0-9_.-]{20,}", re.IGNORECASE),
    re.compile(r"OUTLOOK_EMAIL_PLUS_API_KEY=(?!<your-api-key>)[A-Za-z0-9_.-]{20,}", re.IGNORECASE),
]


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    name: str
    message: str


class SmokeError(RuntimeError):
    pass


def smoke_endpoints() -> dict[str, str]:
    return {
        "health": CANONICAL_HEALTH,
        "capabilities": CANONICAL_CAPABILITIES,
        "integration_bundle": CANONICAL_INTEGRATION_BUNDLE,
        "providers": CANONICAL_PROVIDERS,
        "mailboxes": f"{CANONICAL_MAILBOXES}?page_size=1",
        "openapi": CANONICAL_OPENAPI,
    }


def build_report(results: list[CheckResult]) -> dict[str, Any]:
    checks = [{"ok": result.ok, "name": result.name, "message": result.message} for result in results]
    failures = [check for check in checks if not check["ok"]]
    return {
        "success": not failures,
        "total": len(checks),
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "endpoints": smoke_endpoints(),
        "checks": checks,
        "failures": failures,
    }


def build_error_report(message: str) -> dict[str, Any]:
    return {
        "success": False,
        "code": "SMOKE_ERROR",
        "message": message,
        "endpoints": smoke_endpoints(),
    }


def _join_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def fetch_json(base_url: str, api_key: str, path: str, *, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(
        _join_url(base_url, path),
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SmokeError(f"GET {path} failed with HTTP {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise SmokeError(f"GET {path} failed: {exc.reason}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SmokeError(f"GET {path} did not return JSON") from exc
    if not isinstance(parsed, dict):
        raise SmokeError(f"GET {path} returned a non-object JSON payload")
    return parsed


def _envelope_data(payload: dict[str, Any], name: str) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    if payload.get("openapi"):
        return payload
    raise SmokeError(f"{name} response does not contain an object data field")


def _check(condition: bool, name: str, message: str) -> CheckResult:
    return CheckResult(bool(condition), name, message)


def _missing_keys(value: Any, required: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return sorted(required)
    return sorted(required - set(value))


def _dict_has_non_negative_ints(value: Any, required: set[str]) -> bool:
    if not isinstance(value, dict):
        return False
    for key in required:
        item = value.get(key)
        if not isinstance(item, int) or item < 0:
            return False
    return True


def _health_readiness_checks(readiness: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    missing = _missing_keys(readiness, REQUIRED_HEALTH_READINESS_SECTIONS)
    results.append(
        _check(
            isinstance(readiness, dict) and not missing,
            "health.readiness",
            "health readiness exposes required operational sections",
        )
    )
    results.append(
        _check(
            readiness.get("status") in {"ready", "degraded"},
            "health.readiness.status",
            "health readiness status is ready or degraded",
        )
    )
    discovery = readiness.get("discovery") if isinstance(readiness.get("discovery"), dict) else {}
    next_endpoints = discovery.get("next_endpoints") if isinstance(discovery.get("next_endpoints"), dict) else {}
    for key, expected_path in REQUIRED_HEALTH_DISCOVERY_ENDPOINTS.items():
        results.append(
            _check(
                next_endpoints.get(key) == expected_path,
                f"health.readiness.discovery.{key}",
                f"health readiness points {key} at canonical v1 endpoint",
            )
        )
    providers = readiness.get("providers") if isinstance(readiness.get("providers"), dict) else {}
    provider_summary = providers.get("summary") if isinstance(providers.get("summary"), dict) else {}
    results.append(
        _check(
            _dict_has_non_negative_ints(provider_summary, REQUIRED_PROVIDER_SUMMARY_FIELDS),
            "health.readiness.providers.summary",
            "health readiness provider summary exposes non-negative counters",
        )
    )
    mailbox_directory = readiness.get("mailbox_directory") if isinstance(readiness.get("mailbox_directory"), dict) else {}
    mailbox_totals = mailbox_directory.get("totals") if isinstance(mailbox_directory.get("totals"), dict) else {}
    results.append(
        _check(
            mailbox_directory.get("endpoint") == CANONICAL_MAILBOXES,
            "health.readiness.mailbox_directory.endpoint",
            "health readiness mailbox directory points at canonical v1 endpoint",
        )
    )
    results.append(
        _check(
            _dict_has_non_negative_ints(mailbox_totals, {"mailboxes", "account_mailboxes", "temp_mailboxes"}),
            "health.readiness.mailbox_directory.totals",
            "health readiness mailbox directory exposes non-negative totals",
        )
    )
    task_temp = readiness.get("task_temp_mailbox") if isinstance(readiness.get("task_temp_mailbox"), dict) else {}
    results.append(
        _check(
            task_temp.get("provider_selector_field") == "provider_name",
            "health.readiness.task_temp_mailbox.provider_selector_field",
            "task temp readiness exposes provider_name selector",
        )
    )
    results.append(
        _check(
            task_temp.get("apply_endpoint") == f"{CANONICAL_EXTERNAL_PREFIX}/temp-emails/apply",
            "health.readiness.task_temp_mailbox.apply_endpoint",
            "task temp readiness points apply endpoint at canonical v1",
        )
    )
    return results


def _provider_readiness_summary_checks(prefix: str, readiness: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.append(_check(readiness.get("version") == 1, f"{prefix}.readiness.version", f"{prefix} readiness version is 1"))
    results.append(
        _check(
            readiness.get("overall_status") in {"ready", "needs_config", "degraded"},
            f"{prefix}.readiness.overall_status",
            f"{prefix} readiness exposes an operator status",
        )
    )
    totals = readiness.get("totals") if isinstance(readiness.get("totals"), dict) else {}
    issues = readiness.get("issues") if isinstance(readiness.get("issues"), dict) else {}
    selector_fields = readiness.get("provider_selector_fields") if isinstance(readiness.get("provider_selector_fields"), dict) else {}
    endpoints = readiness.get("endpoints") if isinstance(readiness.get("endpoints"), dict) else {}
    provider_rows = readiness.get("providers") if isinstance(readiness.get("providers"), list) else []
    results.append(
        _check(
            _dict_has_non_negative_ints(totals, REQUIRED_PROVIDER_READINESS_TOTALS),
            f"{prefix}.readiness.totals",
            f"{prefix} readiness totals expose non-negative provider and mailbox counters",
        )
    )
    results.append(
        _check(
            _dict_has_non_negative_ints(issues, REQUIRED_PROVIDER_READINESS_ISSUES),
            f"{prefix}.readiness.issues",
            f"{prefix} readiness issues expose non-negative counters",
        )
    )
    results.append(
        _check(
            all(selector_fields.get(key) == value for key, value in REQUIRED_PROVIDER_SELECTOR_FIELDS.items()),
            f"{prefix}.readiness.provider_selector_fields",
            f"{prefix} readiness exposes pool and task-temp selector fields",
        )
    )
    results.append(
        _check(
            endpoints.get("provider_preflight") == CANONICAL_PROVIDER_PREFLIGHT,
            f"{prefix}.readiness.endpoints.provider_preflight",
            f"{prefix} readiness points provider preflight at canonical v1",
        )
    )
    results.append(
        _check(
            isinstance(provider_rows, list),
            f"{prefix}.readiness.providers",
            f"{prefix} readiness exposes compact provider rows",
        )
    )
    for index, provider in enumerate(provider_rows[:5]):
        required_row_keys = {
            "kind",
            "provider",
            "label",
            "active",
            "configured",
            "readiness_status",
            "mailbox_count",
            "account_count",
            "temp_count",
            "can_dynamic_create",
            "requires_pool_inventory",
            "read_capability",
            "missing_config_count",
            "endpoints",
        }
        missing_row_keys = _missing_keys(provider, required_row_keys)
        results.append(
            _check(
                isinstance(provider, dict) and not missing_row_keys,
                f"{prefix}.readiness.providers[{index}]",
                f"{prefix} provider row exposes compact readiness fields",
            )
        )
    return results


def _routing_matrix_checks(prefix: str, routing_matrix: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    is_versioned = isinstance(routing_matrix, dict) and routing_matrix.get("version") == 1
    results.append(_check(is_versioned, f"{prefix}.routing_matrix.version", f"{prefix} routing matrix version is 1"))
    scopes = routing_matrix.get("scopes") if isinstance(routing_matrix.get("scopes"), dict) else {}
    missing_scopes = sorted(REQUIRED_ROUTING_SCOPES - set(scopes))
    results.append(
        _check(
            not missing_scopes,
            f"{prefix}.routing_matrix.scopes",
            f"{prefix} routing matrix includes required scopes",
        )
    )
    for scope_name in sorted(REQUIRED_ROUTING_SCOPES):
        scope = scopes.get(scope_name) if isinstance(scopes.get(scope_name), dict) else {}
        allowed_values = scope.get("allowed_values") if isinstance(scope.get("allowed_values"), list) else []
        providers = scope.get("providers") if isinstance(scope.get("providers"), list) else []
        counts = scope.get("counts") if isinstance(scope.get("counts"), dict) else {}
        results.append(
            _check(
                bool(str(scope.get("request_field") or "").strip()),
                f"{prefix}.routing_matrix.{scope_name}.request_field",
                f"{scope_name} exposes a request field",
            )
        )
        results.append(
            _check(
                isinstance(scope.get("endpoint"), str),
                f"{prefix}.routing_matrix.{scope_name}.endpoint",
                f"{scope_name} exposes an endpoint string",
            )
        )
        results.append(
            _check(
                bool(allowed_values),
                f"{prefix}.routing_matrix.{scope_name}.allowed_values",
                f"{scope_name} exposes allowed provider values",
            )
        )
        results.append(
            _check(
                isinstance(counts.get("total"), int) and counts.get("total") == len(providers),
                f"{prefix}.routing_matrix.{scope_name}.counts",
                f"{scope_name} count total matches provider rows",
            )
        )
        results.append(
            _check(
                all(isinstance(provider, dict) and provider.get("provider") for provider in providers),
                f"{prefix}.routing_matrix.{scope_name}.providers",
                f"{scope_name} provider rows expose provider keys",
            )
        )
    return results


def _integration_bundle_checks(bundle: dict[str, Any], *, capabilities: dict[str, Any], openapi_payload: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    required = {
        "version",
        "service",
        "status",
        "auth",
        "endpoints",
        "legacy_endpoints",
        "compatibility",
        "documentation",
        "quickstart",
        "readiness",
        "provider_selection",
        "openapi",
        "workflows",
        "smoke_checks",
        "recommendations",
        "action_plan",
    }
    missing = _missing_keys(bundle, required)
    results.append(_check(isinstance(bundle, dict) and not missing, "integration_bundle", "integration bundle exposes required sections"))
    results.append(
        _check(
            bundle.get("status") in {"ready", "needs_config", "degraded"},
            "integration_bundle.status",
            "integration bundle exposes an operator status",
        )
    )
    auth = bundle.get("auth") if isinstance(bundle.get("auth"), dict) else {}
    results.append(
        _check(
            auth.get("header") == "X-API-Key" and auth.get("placeholder") == "<your-api-key>",
            "integration_bundle.auth",
            "integration bundle uses placeholder API-key auth",
        )
    )
    endpoints = bundle.get("endpoints") if isinstance(bundle.get("endpoints"), dict) else {}
    results.append(
        _check(
            endpoints.get("integration_bundle") == CANONICAL_INTEGRATION_BUNDLE,
            "integration_bundle.endpoints.integration_bundle",
            "integration bundle points at canonical v1 endpoint",
        )
    )
    readiness = bundle.get("readiness") if isinstance(bundle.get("readiness"), dict) else {}
    provider_selection = bundle.get("provider_selection") if isinstance(bundle.get("provider_selection"), dict) else {}
    openapi = bundle.get("openapi") if isinstance(bundle.get("openapi"), dict) else {}
    smoke_checks = bundle.get("smoke_checks") if isinstance(bundle.get("smoke_checks"), list) else []
    recommendation_rows = bundle.get("recommendations") if isinstance(bundle.get("recommendations"), list) else []
    action_plan = bundle.get("action_plan") if isinstance(bundle.get("action_plan"), dict) else {}
    results.append(
        _check(
            (readiness.get("external_api") or {}).get("discovery", {}).get("next_endpoints", {}).get("integration_bundle") == CANONICAL_INTEGRATION_BUNDLE,
            "integration_bundle.readiness.discovery",
            "bundle readiness points health discovery at the bundle endpoint",
        )
    )
    results.append(
        _check(
            provider_selection.get("selector_fields") == REQUIRED_PROVIDER_SELECTOR_FIELDS,
            "integration_bundle.provider_selection.selector_fields",
            "bundle provider selection exposes pool and task-temp selectors",
        )
    )
    paths = openapi_payload.get("paths") if isinstance(openapi_payload.get("paths"), dict) else {}
    schemas = ((openapi_payload.get("components") or {}).get("schemas") or {}) if isinstance(openapi_payload, dict) else {}
    results.append(
        _check(
            openapi.get("endpoint") == CANONICAL_OPENAPI and openapi.get("path_count") == len(paths) and openapi.get("schema_count") == len(schemas),
            "integration_bundle.openapi",
            "bundle OpenAPI metadata matches the generated contract",
        )
    )
    smoke_keys = {str(item.get("key")) for item in smoke_checks if isinstance(item, dict)}
    results.append(
        _check(
            {"health", "capabilities", "integration_bundle", "providers", "mailboxes", "openapi"}.issubset(smoke_keys),
            "integration_bundle.smoke_checks",
            "bundle lists read-only smoke-check endpoints",
        )
    )
    recommendation_keys = {str(item.get("key")) for item in recommendation_rows if isinstance(item, dict)}
    results.append(
        _check(
            "generate_client" in recommendation_keys,
            "integration_bundle.recommendations",
            "bundle includes a client-generation recommendation",
        )
    )
    results.extend(_integration_bundle_action_plan_checks(action_plan, bundle_status=str(bundle.get("status") or "")))
    results.append(
        _check(
            bundle.get("quickstart") == capabilities.get("quickstart"),
            "integration_bundle.quickstart",
            "bundle quickstart matches capabilities quickstart",
        )
    )
    return results


def _integration_bundle_action_plan_checks(action_plan: dict[str, Any], *, bundle_status: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    required = {"version", "status", "summary", "items"}
    missing = _missing_keys(action_plan, required)
    results.append(
        _check(
            isinstance(action_plan, dict) and not missing,
            "integration_bundle.action_plan",
            "bundle exposes a versioned machine-readable action plan",
        )
    )
    results.append(
        _check(
            action_plan.get("version") == 1 and action_plan.get("status") in {"ready", "needs_config", "degraded"},
            "integration_bundle.action_plan.version_status",
            "action plan exposes version and readiness status",
        )
    )
    items = action_plan.get("items") if isinstance(action_plan.get("items"), list) else []
    summary = action_plan.get("summary") if isinstance(action_plan.get("summary"), dict) else {}
    summary_fields = ("total", "blocking", "high", "medium", "low")
    results.append(
        _check(
            all(isinstance(summary.get(field), int) and summary.get(field) >= 0 for field in summary_fields)
            and summary.get("total") == len(items),
            "integration_bundle.action_plan.summary",
            "action plan summary counters are non-negative and match item count",
        )
    )
    required_item_fields = {"key", "priority", "status", "blocking", "title", "detail"}
    malformed = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            malformed.append(str(index))
            continue
        missing_fields = _missing_keys(item, required_item_fields)
        if missing_fields:
            malformed.append(f"{item.get('key') or index}:missing")
            continue
        if item.get("priority") not in ACTION_PLAN_PRIORITIES:
            malformed.append(f"{item.get('key')}:priority")
        if item.get("status") not in ACTION_PLAN_STATUSES:
            malformed.append(f"{item.get('key')}:status")
        if not isinstance(item.get("blocking"), bool):
            malformed.append(f"{item.get('key')}:blocking")
        if not (item.get("endpoint") or item.get("command") or item.get("docs")):
            malformed.append(f"{item.get('key')}:target")
    results.append(
        _check(
            not malformed,
            "integration_bundle.action_plan.items",
            "action plan items expose required fields, valid states, and an actionable target",
        )
    )
    item_keys = [str(item.get("key") or "") for item in items if isinstance(item, dict)]
    results.append(
        _check(
            "run_smoke_check" in item_keys,
            "integration_bundle.action_plan.run_smoke_check",
            "action plan includes the read-only smoke check",
        )
    )
    results.append(
        _check(
            bundle_status != "ready" or "start_mailbox_session" in item_keys,
            "integration_bundle.action_plan.start_mailbox_session",
            "ready action plan exposes mailbox session startup",
        )
    )
    serialized = json.dumps(action_plan, ensure_ascii=False)
    placeholder_safe = "<your-api-key>" in serialized and "<your-base-url>" in serialized
    results.append(
        _check(
            placeholder_safe and "OUTLOOK_EMAIL_PLUS_API_KEY=" in serialized and "OUTLOOK_EMAIL_PLUS_API_KEY=<your-api-key>" in serialized,
            "integration_bundle.action_plan.placeholder_command",
            "action plan commands use placeholder API key and base URL values",
        )
    )
    return results


def validate_contracts(
    *,
    health_payload: dict[str, Any],
    capabilities_payload: dict[str, Any],
    integration_bundle_payload: dict[str, Any],
    providers_payload: dict[str, Any],
    mailboxes_payload: dict[str, Any],
    openapi_payload: dict[str, Any],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    health_data = _envelope_data(health_payload, "health")
    capabilities = _envelope_data(capabilities_payload, "capabilities")
    integration_bundle = _envelope_data(integration_bundle_payload, "integration_bundle")
    providers = _envelope_data(providers_payload, "providers")
    mailboxes = _envelope_data(mailboxes_payload, "mailboxes")
    manifest = capabilities.get("integration_manifest") if isinstance(capabilities.get("integration_manifest"), dict) else {}
    quickstart = capabilities.get("quickstart") if isinstance(capabilities.get("quickstart"), dict) else {}
    manifest_quickstart = manifest.get("quickstart") if isinstance(manifest.get("quickstart"), dict) else {}
    documentation = capabilities.get("documentation") if isinstance(capabilities.get("documentation"), dict) else {}
    endpoints = capabilities.get("endpoints") if isinstance(capabilities.get("endpoints"), dict) else {}
    legacy_endpoints = capabilities.get("legacy_endpoints") if isinstance(capabilities.get("legacy_endpoints"), dict) else {}
    compatibility = capabilities.get("compatibility") if isinstance(capabilities.get("compatibility"), dict) else {}
    mailbox_session = capabilities.get("mailbox_session") if isinstance(capabilities.get("mailbox_session"), dict) else {}
    workflows = manifest.get("workflows") if isinstance(manifest.get("workflows"), list) else []
    workflow_keys = {str(item.get("key")) for item in workflows if isinstance(item, dict)}
    schemas = ((openapi_payload.get("components") or {}).get("schemas") or {}) if isinstance(openapi_payload, dict) else {}
    paths = openapi_payload.get("paths") if isinstance(openapi_payload.get("paths"), dict) else {}
    openapi_legacy_endpoints = (
        openapi_payload.get("x-legacy-endpoints") if isinstance(openapi_payload.get("x-legacy-endpoints"), dict) else {}
    )
    provider_readiness = providers.get("readiness_summary") if isinstance(providers.get("readiness_summary"), dict) else {}
    provider_routing_matrix = (
        provider_readiness.get("routing_matrix") if isinstance(provider_readiness.get("routing_matrix"), dict) else {}
    )
    provider_context = mailboxes.get("provider_context") if isinstance(mailboxes.get("provider_context"), dict) else {}
    mailbox_readiness = (
        provider_context.get("readiness_summary") if isinstance(provider_context.get("readiness_summary"), dict) else {}
    )
    mailbox_routing_matrix = (
        mailbox_readiness.get("routing_matrix") if isinstance(mailbox_readiness.get("routing_matrix"), dict) else {}
    )
    health_readiness = health_data.get("readiness") if isinstance(health_data.get("readiness"), dict) else {}
    manifest_discovery = manifest.get("discovery") if isinstance(manifest.get("discovery"), dict) else {}
    manifest_discovery_endpoints = (
        manifest_discovery.get("endpoints") if isinstance(manifest_discovery.get("endpoints"), dict) else {}
    )

    results.append(
        _check(
            bool(health_data.get("status") or health_data.get("service")),
            "health",
            "health endpoint returned service data",
        )
    )
    for key in (
        "integration_manifest",
        "integration_bundle",
        "quickstart",
        "documentation",
        "endpoints",
        "mailbox_session",
        "external_mailbox_read_contract",
    ):
        results.append(_check(key in capabilities, f"capabilities.{key}", f"capabilities exposes {key}"))
    results.extend(_health_readiness_checks(health_readiness))
    results.extend(_integration_bundle_checks(integration_bundle, capabilities=capabilities, openapi_payload=openapi_payload))
    results.append(
        _check(
            bool(quickstart) and quickstart == manifest_quickstart,
            "quickstart.parity",
            "top-level quickstart matches integration_manifest.quickstart",
        )
    )
    results.append(
        _check(
            (manifest.get("auth") or {}).get("header") == "X-API-Key",
            "manifest.auth.header",
            "manifest auth header is X-API-Key",
        )
    )
    results.append(
        _check(
            (manifest.get("auth") or {}).get("placeholder") == "<your-api-key>",
            "manifest.auth.placeholder",
            "manifest uses placeholder API key",
        )
    )
    missing_workflows = sorted(REQUIRED_WORKFLOWS - workflow_keys)
    results.append(
        _check(
            not missing_workflows,
            "manifest.workflows",
            f"required workflows present: {', '.join(sorted(REQUIRED_WORKFLOWS))}",
        )
    )
    results.append(
        _check(
            endpoints.get("docs") == CANONICAL_DOCS,
            "endpoints.docs",
            "docs endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            endpoints.get("integration_bundle") == CANONICAL_INTEGRATION_BUNDLE,
            "endpoints.integration_bundle",
            "integration bundle endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            endpoints.get("openapi") == CANONICAL_OPENAPI,
            "endpoints.openapi",
            "OpenAPI endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            endpoints.get("providers") == CANONICAL_PROVIDERS,
            "endpoints.providers",
            "providers endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            endpoints.get("provider_preflight") == CANONICAL_PROVIDER_PREFLIGHT,
            "endpoints.provider_preflight",
            "provider preflight endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            endpoints.get("mailboxes") == CANONICAL_MAILBOXES,
            "endpoints.mailboxes",
            "mailbox directory endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            quickstart.get("endpoints", {}).get("provider_preflight") == CANONICAL_PROVIDER_PREFLIGHT,
            "quickstart.endpoints.provider_preflight",
            "quickstart exposes provider preflight endpoint",
        )
    )
    results.append(
        _check(
            manifest_discovery_endpoints.get("docs") == CANONICAL_DOCS,
            "manifest.discovery.endpoints.docs",
            "integration manifest discovery exposes docs endpoint",
        )
    )
    results.append(
        _check(
            manifest_discovery_endpoints.get("integration_bundle") == CANONICAL_INTEGRATION_BUNDLE,
            "manifest.discovery.endpoints.integration_bundle",
            "integration manifest discovery exposes integration bundle endpoint",
        )
    )
    results.append(
        _check(
            manifest_discovery_endpoints.get("provider_preflight") == CANONICAL_PROVIDER_PREFLIGHT,
            "manifest.discovery.endpoints.provider_preflight",
            "integration manifest discovery exposes provider preflight endpoint",
        )
    )
    results.append(
        _check(
            endpoints.get("mailbox_session_start") == CANONICAL_SESSION_START,
            "endpoints.mailbox_session_start",
            "mailbox session endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            endpoints.get("mailbox_session_close") == CANONICAL_SESSION_CLOSE,
            "endpoints.mailbox_session_close",
            "mailbox session close endpoint is canonical v1",
        )
    )
    results.append(
        _check(
            mailbox_session.get("start_endpoint") == CANONICAL_SESSION_START,
            "mailbox_session.start_endpoint",
            "mailbox session discovery points at canonical v1 start endpoint",
        )
    )
    results.append(
        _check(
            mailbox_session.get("close_endpoint") == CANONICAL_SESSION_CLOSE,
            "mailbox_session.close_endpoint",
            "mailbox session discovery points at canonical v1 close endpoint",
        )
    )
    results.append(
        _check(
            legacy_endpoints == {},
            "legacy_endpoints.empty",
            "legacy endpoint map is empty after legacy route removal",
        )
    )
    results.append(
        _check(
            compatibility.get("legacy_supported") is False,
            "compatibility.legacy_supported",
            "legacy external API routes are explicitly unsupported",
        )
    )
    results.append(
        _check(
            compatibility.get("canonical_prefix") == CANONICAL_EXTERNAL_PREFIX,
            "compatibility.canonical_prefix",
            "compatibility contract names the canonical v1 prefix",
        )
    )
    results.append(
        _check(
            compatibility.get("legacy_prefix") == LEGACY_EXTERNAL_PREFIX,
            "compatibility.legacy_prefix",
            "compatibility contract still names the removed legacy prefix for migration",
        )
    )
    results.append(
        _check(
            (compatibility.get("aliases") or {}) == {},
            "compatibility.aliases.empty",
            "compatibility aliases are empty after legacy route removal",
        )
    )
    results.append(
        _check(
            mailbox_session.get("source_strategy_values") == EXPECTED_STRATEGIES,
            "mailbox_session.source_strategy_values",
            "mailbox session strategies are complete",
        )
    )
    doc_entries = documentation.get("entries") if isinstance(documentation.get("entries"), dict) else {}
    results.append(
        _check(
            "external_integration_quickstart" in doc_entries,
            "documentation.external_integration_quickstart",
            "documentation links the external integration quickstart",
        )
    )
    results.append(
        _check(
            (doc_entries.get("api_docs") or {}).get("endpoint") == CANONICAL_DOCS,
            "documentation.api_docs.endpoint",
            "documentation points API docs at canonical v1 endpoint",
        )
    )
    results.append(
        _check(
            (doc_entries.get("openapi") or {}).get("endpoint") == CANONICAL_OPENAPI,
            "documentation.openapi.endpoint",
            "documentation points OpenAPI at canonical v1 endpoint",
        )
    )
    results.append(
        _check(
            CANONICAL_DOCS in paths,
            "openapi.path.docs",
            "OpenAPI exposes canonical v1 docs path",
        )
    )
    results.append(
        _check(
            CANONICAL_INTEGRATION_BUNDLE in paths,
            "openapi.path.integration_bundle",
            "OpenAPI exposes canonical v1 integration bundle path",
        )
    )
    results.append(
        _check(
            CANONICAL_PROVIDER_PREFLIGHT in paths,
            "openapi.path.provider_preflight",
            "OpenAPI exposes canonical v1 provider preflight path",
        )
    )
    results.append(
        _check(
            CANONICAL_SESSION_START in paths,
            "openapi.path.mailbox_session_start",
            "OpenAPI exposes canonical v1 mailbox session start path",
        )
    )
    results.append(
        _check(
            CANONICAL_SESSION_CLOSE in paths,
            "openapi.path.mailbox_session_close",
            "OpenAPI exposes canonical v1 mailbox session close path",
        )
    )
    results.append(
        _check(
            LEGACY_DOCS not in paths
            and LEGACY_INTEGRATION_BUNDLE not in paths
            and LEGACY_PROVIDER_PREFLIGHT not in paths
            and LEGACY_SESSION_START not in paths
            and LEGACY_SESSION_CLOSE not in paths,
            "openapi.path.legacy_not_duplicated",
            "OpenAPI does not duplicate legacy operations in paths",
        )
    )
    results.append(
        _check(
            openapi_legacy_endpoints == {},
            "openapi.x_legacy_endpoints.empty",
            "OpenAPI does not advertise legacy endpoint metadata",
        )
    )
    for schema_name in (
        "MailboxSessionStartRequest",
        "MailboxSessionCloseRequest",
        "MailboxSessionData",
        "MailboxSessionCloseData",
        "MailboxSessionDiscovery",
        "IntegrationBundleData",
    ):
        results.append(_check(schema_name in schemas, f"openapi.schema.{schema_name}", f"OpenAPI includes {schema_name}"))
    results.extend(_provider_readiness_summary_checks("providers", provider_readiness))
    results.extend(_provider_readiness_summary_checks("mailboxes", mailbox_readiness))
    results.extend(_routing_matrix_checks("providers", provider_routing_matrix))
    results.extend(_routing_matrix_checks("mailboxes", mailbox_routing_matrix))
    serialized = json.dumps(
        {"capabilities": capabilities, "integration_bundle": integration_bundle, "providers": providers, "mailboxes": mailboxes, "openapi": openapi_payload},
        ensure_ascii=False,
    )
    secret_hits = [pattern.pattern for pattern in SECRET_PATTERNS if pattern.search(serialized)]
    results.append(
        _check(not secret_hits, "secret_scan.discovery_payload", "discovery payload does not contain obvious secret values")
    )
    return results


def run_smoke(
    *,
    base_url: str,
    api_key: str,
    timeout: float = 10.0,
    fetcher: Callable[[str, str, str], dict[str, Any]] | None = None,
) -> list[CheckResult]:
    if not base_url.strip():
        raise SmokeError("--base-url is required")
    if not api_key.strip():
        raise SmokeError("API key is required via --api-key or OUTLOOK_EMAIL_PLUS_API_KEY")
    if fetcher is None:
        fetcher = lambda root, key, path: fetch_json(root, key, path, timeout=timeout)
    endpoints = smoke_endpoints()
    health = fetcher(base_url, api_key, endpoints["health"])
    capabilities = fetcher(base_url, api_key, endpoints["capabilities"])
    integration_bundle = fetcher(base_url, api_key, endpoints["integration_bundle"])
    providers = fetcher(base_url, api_key, endpoints["providers"])
    mailboxes = fetcher(base_url, api_key, endpoints["mailboxes"])
    openapi = fetcher(base_url, api_key, endpoints["openapi"])
    return validate_contracts(
        health_payload=health,
        capabilities_payload=capabilities,
        integration_bundle_payload=integration_bundle,
        providers_payload=providers,
        mailboxes_payload=mailboxes,
        openapi_payload=openapi,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only smoke check for Outlook Email Plus external API discovery contracts."
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL of the Outlook Email Plus instance, for example https://mailbox.example.com",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OUTLOOK_EMAIL_PLUS_API_KEY", ""),
        help="External API key. Defaults to OUTLOOK_EMAIL_PLUS_API_KEY.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds. Default: 10")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        results = run_smoke(base_url=args.base_url, api_key=args.api_key, timeout=args.timeout)
    except SmokeError as exc:
        if args.format == "json":
            print(json.dumps(build_error_report(str(exc)), ensure_ascii=False), file=sys.stderr)
            return 2
        print(f"FAIL smoke: {exc}", file=sys.stderr)
        return 2
    failed = [result for result in results if not result.ok]
    if args.format == "json":
        print(json.dumps(build_report(results), ensure_ascii=False))
        return 1 if failed else 0
    for result in results:
        prefix = "OK" if result.ok else "FAIL"
        print(f"{prefix} {result.name}: {result.message}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
