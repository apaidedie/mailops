from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from typing import Any

from mailops import config
from mailops.cors_config import get_external_api_cors_contract
from mailops.errors import sanitize_error_details
from mailops.repositories import settings as settings_repo
from mailops.services.mailbox_directory_contract import get_mailbox_catalog_contract
from mailops.services.providers import MAIL_PROVIDERS, get_provider_list
from mailops.services.temp_mail_provider_base import normalize_provider_capabilities
from mailops.services.temp_mail_provider_factory import TempMailProviderFactoryError, get_available_providers

from .bridge import (
    _canonical_bridge_operator_provider,
    _collapse_bridge_operator_provider_rows,
    _merge_unique_str_list,
    get_operator_temp_mail_default_provider,
)
from .catalog import (
    _PROVIDER_CAPABILITY_READ_ACTIONS,
    _PROVIDER_CAPABILITY_WORKFLOWS,
    _append_unique,
    _normalize_provider_name,
    _provider_readiness_reason,
    _provider_readiness_status,
    _provider_recipe_active,
    _provider_recipe_alias_canonical,
    _provider_recipe_kind,
    _provider_recipe_label,
    _provider_selection_recipe_bundle,
    account_provider_label,
    get_active_account_provider_names,
    get_active_mailbox_provider_filter_contract,
    get_active_temp_provider_names,
    get_mailbox_provider_catalog,
    get_mailbox_provider_default_diagnostics,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_provider_alias_contract,
    get_provider_catalog_item,
    is_mailbox_provider_active,
    mailbox_session_provider_metadata,
    temp_mail_provider_config_status,
    temp_mail_provider_display_label,
    temp_mail_provider_label,
)
from .constants import (
    _BRIDGE_OPERATOR_CANONICAL,
    _BRIDGE_OPERATOR_FAMILY,
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    GPTMAIL_POOL_TEMP_PROVIDER_NAMES,
    GPTMAIL_RUNTIME_ALIASES,
    PROVIDER_SELECTION_SOURCE_PRIORITY,
    TEMP_MAIL_PROVIDER_ENV,
)
from .endpoints import (
    _CANONICAL_EXTERNAL_ENDPOINTS,
    _EXTERNAL_MAILBOX_SESSION_CLOSE_ACTION,
    _EXTERNAL_MAILBOX_SESSION_READ_ACTION,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    _action_contract_next_actions_for_endpoint_map,
    get_external_api_endpoint_map,
    get_external_mailbox_read_contract,
    get_provider_documentation_contract,
)
from .selection import get_mailbox_provider_selection_policy


def _provider_integration_endpoint_map(endpoints: dict[str, Any] | None = None) -> dict[str, str]:
    source = endpoints if isinstance(endpoints, dict) else {}
    defaults = get_external_api_endpoint_map()
    return {key: str(source.get(key) or value) for key, value in defaults.items()}


def _provider_integration_scope(selection_policy: dict[str, Any], scope_name: str) -> dict[str, Any]:
    scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    scope = scopes.get(scope_name) if isinstance(scopes.get(scope_name), dict) else {}
    return copy.deepcopy(scope)


def _provider_integration_aliases_for_provider(item: dict[str, Any], aliases: dict[str, Any]) -> dict[str, list[str]]:
    provider = _normalize_provider_name(item.get("provider"))
    kind = str(item.get("kind") or "").strip().lower()
    account_type = str(item.get("account_type") or "").strip().lower()
    runtime_aliases = (
        aliases.get("runtime_temp_mail_provider_aliases")
        if isinstance(aliases.get("runtime_temp_mail_provider_aliases"), dict)
        else {}
    )
    pool_aliases = (
        aliases.get("pool_claim_provider_aliases") if isinstance(aliases.get("pool_claim_provider_aliases"), dict) else {}
    )

    provider_aliases: dict[str, list[str]] = {
        "runtime_temp_mail_provider": [],
        "pool_claim_provider": [],
        "active_allowlist": [],
    }
    for alias, canonical in runtime_aliases.items():
        if _normalize_provider_name(canonical) == provider:
            provider_aliases["runtime_temp_mail_provider"].append(str(alias))
            provider_aliases["active_allowlist"].append(str(alias))
    for alias, raw_info in pool_aliases.items():
        info = raw_info if isinstance(raw_info, dict) else {}
        canonical_provider = _normalize_provider_name(info.get("canonical_provider"))
        temp_provider_names = {_normalize_provider_name(value) for value in (info.get("temp_provider_names") or [])}
        if canonical_provider == provider or provider in temp_provider_names:
            provider_aliases["pool_claim_provider"].append(str(alias))
            provider_aliases["active_allowlist"].append(str(alias))
    if kind == "account" and account_type == "imap":
        provider_aliases["active_allowlist"].append("imap")
    return {key: sorted(set(values)) for key, values in provider_aliases.items()}


def _provider_config_file_example(key: str, value: Any) -> dict[str, Any]:
    return {"section": "providers", "key": key, "value": copy.deepcopy(value)}


def _provider_deployment_step(raw_step: dict[str, Any], *, config_key: str, config_value: Any) -> dict[str, Any]:
    step = raw_step if isinstance(raw_step, dict) else {}
    env_key = str(step.get("env") or "").strip()
    settings_key = str(step.get("settings_key") or "").strip()
    value = copy.deepcopy(step.get("value") if "value" in step else config_value)
    result: dict[str, Any] = {"provider_config": _provider_config_file_example(config_key, config_value)}
    if env_key:
        result["env"] = {"key": env_key, "value": copy.deepcopy(value)}
    if settings_key:
        result["settings"] = {
            "key": settings_key,
            "value": copy.deepcopy(step.get("settings_value") if "settings_value" in step else value),
        }
    return result


def _provider_request_step(raw_step: dict[str, Any], *, endpoint: str, body_fields: list[str]) -> dict[str, Any]:
    step = raw_step if isinstance(raw_step, dict) else {}
    return {
        "method": "POST",
        "endpoint": endpoint,
        "field": str(step.get("field") or ""),
        "value": copy.deepcopy(step.get("value")),
        "body_fields": list(body_fields),
    }


def _provider_integration_entry(
    item: dict[str, Any],
    *,
    diagnostic: dict[str, Any],
    deployment_profile: dict[str, Any],
    selection_policy: dict[str, Any],
    endpoints: dict[str, str],
) -> dict[str, Any]:
    provider = _normalize_provider_name(item.get("provider"))
    kind = str(item.get("kind") or "").strip().lower()
    deployment = item.get("deployment") if isinstance(item.get("deployment"), dict) else {}
    configuration = item.get("configuration") if isinstance(item.get("configuration"), dict) else {}
    aliases = deployment_profile.get("aliases") if isinstance(deployment_profile.get("aliases"), dict) else {}
    capabilities = {
        "read_capability": item.get("read_capability") or "",
        "requires_pool_inventory": bool(item.get("requires_pool_inventory")),
        "can_dynamic_create": bool(item.get("can_dynamic_create")),
        "can_delete_mailbox": bool(item.get("can_delete_mailbox")),
        "can_delete_message": bool(item.get("can_delete_message")),
        "can_clear_messages": bool(item.get("can_clear_messages")),
    }

    entry: dict[str, Any] = {
        "provider": provider,
        "label": item.get("label") or provider,
        "kind": kind,
        "active": bool(diagnostic.get("active", item.get("active", True))),
        "configured": bool(diagnostic.get("configured", item.get("configured", True))),
        "readiness_status": diagnostic.get("status") or _provider_readiness_status(item),
        "readiness_reason": diagnostic.get("status_reason")
        or _provider_readiness_reason(item, _provider_readiness_status(item)),
        "missing_config": list(diagnostic.get("missing_config") or item.get("missing_config") or []),
        "required_env": list(diagnostic.get("required_env") or configuration.get("required_env") or []),
        "optional_env": list(diagnostic.get("optional_env") or configuration.get("optional_env") or []),
        "required_settings": list(diagnostic.get("required_settings") or configuration.get("required_settings") or []),
        "settings_keys": list(diagnostic.get("settings_keys") or configuration.get("settings_keys") or []),
        "secret_env": list(diagnostic.get("secret_env") or configuration.get("secret_env") or []),
        "secret_settings": list(diagnostic.get("secret_settings") or configuration.get("secret_settings") or []),
        "configuration": {
            "required_env": list(configuration.get("required_env") or []),
            "optional_env": list(configuration.get("optional_env") or []),
            "env_defaults": copy.deepcopy(configuration.get("env_defaults") or {}),
            "settings_keys": list(configuration.get("settings_keys") or []),
            "required_settings": list(configuration.get("required_settings") or []),
            "settings_defaults": copy.deepcopy(configuration.get("settings_defaults") or {}),
            "secret_env": list(configuration.get("secret_env") or []),
            "secret_settings": list(configuration.get("secret_settings") or []),
        },
        "activation": _provider_deployment_step(
            deployment.get("activate") if isinstance(deployment.get("activate"), dict) else {},
            config_key="active_mailbox_providers",
            config_value=[provider],
        ),
        "pool_claim_default": _provider_deployment_step(
            deployment.get("pool_claim_default") if isinstance(deployment.get("pool_claim_default"), dict) else {},
            config_key="pool_default_provider",
            config_value=provider,
        ),
        "pool_claim_request": _provider_request_step(
            deployment.get("pool_claim_request") if isinstance(deployment.get("pool_claim_request"), dict) else {},
            endpoint=endpoints["pool_claim_random"],
            body_fields=["caller_id", "task_id", "provider", "email_domain", "project_key"],
        ),
        "mailbox_directory_filter": {
            "method": "GET",
            "endpoint": endpoints["mailboxes"],
            "query": {"kind": kind or "all", "provider": provider},
        },
        "health": {
            "method": "GET",
            "endpoint": endpoints["provider_health"],
            "path": {"kind": kind, "provider": provider},
            "query_fields": ["probe_network"],
        },
        "endpoints": {
            "capabilities": endpoints["capabilities"],
            "providers": endpoints["providers"],
            "provider_health": endpoints["provider_health"],
            "provider_preflight": endpoints["provider_preflight"],
            "mailboxes": endpoints["mailboxes"],
            "pool_claim_random": endpoints["pool_claim_random"],
        },
        "aliases": _provider_integration_aliases_for_provider(item, aliases),
        "capabilities": capabilities,
        "contract_validation": copy.deepcopy(item.get("contract_validation") or diagnostic.get("contract_validation") or {}),
        "selection_policy_scopes": {
            "active_allowlist": _provider_integration_scope(selection_policy, "active_allowlist"),
            "pool_claim_default": _provider_integration_scope(selection_policy, "pool_claim_default"),
            "explicit_pool_claim": _provider_integration_scope(selection_policy, "explicit_pool_claim"),
        },
    }
    if kind == "temp":
        runtime_step = deployment.get("runtime_default") if isinstance(deployment.get("runtime_default"), dict) else {}
        apply_step = (
            deployment.get("task_temp_apply_request") if isinstance(deployment.get("task_temp_apply_request"), dict) else {}
        )
        entry["runtime_default"] = _provider_deployment_step(
            runtime_step,
            config_key="temp_mail_provider",
            config_value=provider,
        )
        entry["task_temp_apply_request"] = _provider_request_step(
            apply_step,
            endpoint=endpoints["temp_mail_apply"],
            body_fields=["caller_id", "task_id", "prefix", "domain", "provider_name"],
        )
        entry["endpoints"]["temp_mail_apply"] = endpoints["temp_mail_apply"]
        entry["endpoints"]["temp_mail_finish"] = endpoints["temp_mail_finish"]
        entry["selection_policy_scopes"]["temp_runtime_default"] = _provider_integration_scope(
            selection_policy, "temp_runtime_default"
        )
        entry["selection_policy_scopes"]["task_temp_apply"] = _provider_integration_scope(selection_policy, "task_temp_apply")
    if item.get("account_type"):
        entry["account_type"] = item.get("account_type")
    if item.get("config_source"):
        entry["config_source"] = item.get("config_source")
    return entry


def get_provider_integration_guide(
    *,
    catalog: list[dict[str, Any]] | None = None,
    deployment_profile: dict[str, Any] | None = None,
    selection_policy: dict[str, Any] | None = None,
    provider_filter: dict[str, Any] | None = None,
    provider_diagnostics: dict[str, Any] | None = None,
    endpoints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a secret-free, machine-readable guide for external provider integration."""
    # Full catalog may dual-register Compatible Temp Mail Bridge keys for stored
    # source compatibility. Guide projection collapses them so external consumers
    # do not see two identical-label providers.
    raw_catalog = catalog if catalog is not None else get_mailbox_provider_catalog(include_inactive=True, strict=False)
    source_catalog = _collapse_bridge_operator_provider_rows(list(raw_catalog))
    if deployment_profile is None:
        # Deployment profile should still see the full dual-register catalog so
        # allowlist/alias contracts remain complete for accepted historical names.
        deployment_profile = get_mailbox_provider_deployment_profile(catalog=list(raw_catalog), strict=False)
    if selection_policy is None:
        selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    if provider_filter is None:
        provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    if provider_diagnostics is None:
        provider_diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
    guide_endpoints = _provider_integration_endpoint_map(endpoints)
    diagnostics_by_provider = {
        (str(item.get("kind") or "").strip().lower(), _normalize_provider_name(item.get("provider"))): item
        for item in (provider_diagnostics.get("providers") or [])
        if isinstance(item, dict)
    }
    provider_entries = [
        _provider_integration_entry(
            item,
            diagnostic=diagnostics_by_provider.get(
                (
                    str(item.get("kind") or "").strip().lower(),
                    (
                        _canonical_bridge_operator_provider(item.get("provider"))
                        if str(item.get("kind") or "").strip().lower() == "temp"
                        else _normalize_provider_name(item.get("provider"))
                    ),
                ),
                {},
            ),
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            endpoints=guide_endpoints,
        )
        for item in source_catalog
        if _normalize_provider_name(item.get("provider"))
    ]
    selection_scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    recipes = _provider_selection_recipe_bundle(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_integration_guide={"providers": provider_entries},
    )

    return {
        "version": 1,
        "source_priority": list(selection_policy.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY),
        "documentation": get_provider_documentation_contract(),
        "generated_from": [
            "mailbox_provider_catalog",
            "deployment_profile",
            "selection_policy",
            "active_allowlist",
            "provider_diagnostics",
            "external_endpoint_map",
        ],
        "secret_policy": {
            "exposes_secret_values": False,
            "secret_key_names_allowed": True,
            "secret_key_name_fields": ["secret_env", "secret_settings"],
            "forbidden_value_hints": ["api_key", "bearer", "consumer_key", "jwt", "password", "secret", "task_token", "token"],
        },
        "workflow": {
            "discover_capabilities": {
                "method": "GET",
                "endpoint": guide_endpoints["capabilities"],
                "response_field": "provider_integration_guide",
            },
            "discover_providers": {
                "method": "GET",
                "endpoint": guide_endpoints["providers"],
                "response_field": "provider_integration_guide",
            },
            "activate_allowlist": {
                **copy.deepcopy(selection_scopes.get("active_allowlist") or {}),
                "config_file_example": _provider_config_file_example("active_mailbox_providers", []),
            },
            "set_temp_runtime_default": {
                **copy.deepcopy(selection_scopes.get("temp_runtime_default") or {}),
                "config_file_example": _provider_config_file_example("temp_mail_provider", ""),
            },
            "set_pool_claim_default": {
                **copy.deepcopy(selection_scopes.get("pool_claim_default") or {}),
                "config_file_example": _provider_config_file_example("pool_default_provider", "auto"),
            },
            "claim_pool_mailbox": {
                "method": "POST",
                "endpoint": guide_endpoints["pool_claim_random"],
                "request_field": (selection_scopes.get("explicit_pool_claim") or {}).get("request_field") or "provider",
                "body_fields": ["caller_id", "task_id", "provider", "email_domain", "project_key"],
                "allowed_values": list((selection_scopes.get("explicit_pool_claim") or {}).get("allowed_values") or []),
            },
            "create_task_temp_mailbox": {
                "method": "POST",
                "endpoint": guide_endpoints["temp_mail_apply"],
                "request_field": (selection_scopes.get("task_temp_apply") or {}).get("request_field") or "provider_name",
                "body_fields": ["caller_id", "task_id", "prefix", "domain", "provider_name"],
                "allowed_values": list((selection_scopes.get("task_temp_apply") or {}).get("allowed_values") or []),
            },
            "start_mailbox_session": {
                "method": "POST",
                "endpoint": guide_endpoints["mailbox_session_start"],
                "body_fields": [
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
                "source_strategy_values": ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
            },
            "read_mailbox_session": {
                "method": "POST",
                "endpoint": guide_endpoints["mailbox_session_read"],
                "body_fields": list(_EXTERNAL_MAILBOX_SESSION_READ_ACTION["read_session"]["body_fields"]),
                "session_type_values": ["pool_claim", "task_temp_mailbox"],
                "read_action_values": [
                    "messages",
                    "latest_message",
                    "message_detail",
                    "message_raw",
                    "verification_code",
                    "verification_link",
                    "wait_message",
                ],
            },
            "close_mailbox_session": {
                "method": "POST",
                "endpoint": guide_endpoints["mailbox_session_close"],
                "body_fields": [
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
                "session_type_values": ["pool_claim", "task_temp_mailbox"],
            },
            "list_unified_mailboxes": {
                "method": "GET",
                "endpoint": guide_endpoints["mailboxes"],
                "provider_query_field": "provider",
                "provider_context_field": "provider_context",
            },
            "probe_provider_health": {
                "method": "GET",
                "endpoint": guide_endpoints["provider_health"],
                "path_fields": ["kind", "provider"],
                "query_fields": ["probe_network"],
            },
            "preflight_providers": {
                "method": "GET",
                "endpoint": guide_endpoints["provider_preflight"],
                "query_fields": ["probe_network"],
                "response_field": "data",
            },
        },
        "aliases": copy.deepcopy(deployment_profile.get("aliases") or get_provider_alias_contract()),
        "provider_values": copy.deepcopy(deployment_profile.get("provider_values") or {}),
        "selection_recipes": copy.deepcopy(recipes.get("selection_recipes") or []),
        "selection_recipe_index": copy.deepcopy(recipes.get("selection_recipe_index") or {}),
        "provider_filter": copy.deepcopy(provider_filter),
        "endpoints": guide_endpoints,
        "providers": provider_entries,
    }


def _mailbox_inventory_rows(mailbox_inventory: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    inventory = mailbox_inventory if isinstance(mailbox_inventory, dict) else {}
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_item in inventory.get("providers") or []:
        if not isinstance(raw_item, dict):
            continue
        kind = str(raw_item.get("kind") or "").strip().lower()
        provider = _normalize_provider_name(raw_item.get("provider"))
        if not kind or not provider:
            continue
        rows[(kind, provider)] = {
            "kind": kind,
            "provider": provider,
            "label": str(raw_item.get("label") or provider),
            "mailbox_count": int(raw_item.get("mailbox_count") or 0),
            "account_count": int(raw_item.get("account_count") or 0),
            "temp_count": int(raw_item.get("temp_count") or 0),
            "read_capabilities": list(raw_item.get("read_capabilities") or []),
        }
    return rows


def _mailbox_inventory_totals(
    mailbox_inventory: dict[str, Any] | None, inventory_rows: dict[tuple[str, str], dict[str, Any]]
) -> dict[str, int]:
    inventory = mailbox_inventory if isinstance(mailbox_inventory, dict) else {}
    raw_totals = inventory.get("totals") if isinstance(inventory.get("totals"), dict) else {}
    return {
        "mailboxes": int(
            raw_totals.get("mailboxes") or sum(int(row.get("mailbox_count") or 0) for row in inventory_rows.values())
        ),
        "account_mailboxes": int(
            raw_totals.get("account_mailboxes") or sum(int(row.get("account_count") or 0) for row in inventory_rows.values())
        ),
        "temp_mailboxes": int(
            raw_totals.get("temp_mailboxes") or sum(int(row.get("temp_count") or 0) for row in inventory_rows.values())
        ),
    }


def _mailbox_readiness_provider_row(provider: dict[str, Any], inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    item = provider if isinstance(provider, dict) else {}
    inventory = inventory if isinstance(inventory, dict) else {}
    kind = str(item.get("kind") or inventory.get("kind") or "").strip().lower()
    provider_name = _normalize_provider_name(item.get("provider") or inventory.get("provider"))
    capabilities = item.get("capabilities") if isinstance(item.get("capabilities"), dict) else {}
    endpoints = item.get("endpoints") if isinstance(item.get("endpoints"), dict) else {}
    health = item.get("health") if isinstance(item.get("health"), dict) else {}
    missing_config = list(item.get("missing_config") or [])
    read_capabilities = list(inventory.get("read_capabilities") or [])
    read_capability = str(capabilities.get("read_capability") or item.get("read_capability") or "").strip().lower()
    if read_capability and read_capability not in read_capabilities:
        read_capabilities.append(read_capability)
    return {
        "kind": kind,
        "provider": provider_name,
        "label": str(item.get("label") or inventory.get("label") or provider_name),
        "active": bool(item.get("active", True)),
        "configured": bool(item.get("configured", True)),
        "readiness_status": str(item.get("readiness_status") or "unknown"),
        "config_source": str(item.get("config_source") or "catalog"),
        "mailbox_count": int(inventory.get("mailbox_count") or 0),
        "account_count": int(inventory.get("account_count") or 0),
        "temp_count": int(inventory.get("temp_count") or 0),
        "can_dynamic_create": bool(capabilities.get("can_dynamic_create")),
        "requires_pool_inventory": bool(capabilities.get("requires_pool_inventory")),
        "read_capability": read_capability,
        "read_capabilities": read_capabilities,
        "missing_config_count": len(missing_config),
        "endpoints": {
            "health": str(health.get("endpoint") or endpoints.get("provider_health") or PROVIDER_HEALTH_ENDPOINT),
            "mailboxes": str(endpoints.get("mailboxes") or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
        },
    }


_PROVIDER_ROUTING_SCOPE_LABELS = {
    "temp_runtime_default": "Temp runtime default",
    "task_temp_apply": "Task temp-mail apply",
    "pool_claim_default": "Pool claim default",
    "explicit_pool_claim": "Explicit pool claim",
}


def _provider_routing_aliases(provider: str, aliases: dict[str, Any]) -> list[str]:
    values: list[str] = []
    runtime_aliases = (
        aliases.get("runtime_temp_mail_provider_aliases")
        if isinstance(aliases.get("runtime_temp_mail_provider_aliases"), dict)
        else {}
    )
    for alias, canonical in runtime_aliases.items():
        if _normalize_provider_name(canonical) == provider:
            _append_unique(values, [alias])
    pool_aliases = (
        aliases.get("pool_claim_provider_aliases") if isinstance(aliases.get("pool_claim_provider_aliases"), dict) else {}
    )
    for alias, raw_info in pool_aliases.items():
        info = raw_info if isinstance(raw_info, dict) else {}
        canonical = _normalize_provider_name(info.get("canonical_provider"))
        temp_names = {_normalize_provider_name(item) for item in (info.get("temp_provider_names") or [])}
        if canonical == provider or provider in temp_names:
            _append_unique(values, [alias])
    return sorted(set(values))


def _provider_routing_endpoint_for_scope(scope_name: str, scope: dict[str, Any], endpoints: dict[str, str]) -> str:
    explicit_endpoint = str(scope.get("endpoint") or "").strip()
    if explicit_endpoint:
        return explicit_endpoint
    if scope_name in {"explicit_pool_claim", "pool_claim_default"}:
        return str(endpoints.get("pool_claim_random") or _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_random"])
    if scope_name in {"task_temp_apply", "temp_runtime_default"}:
        return str(endpoints.get("temp_mail_apply") or _CANONICAL_EXTERNAL_ENDPOINTS["temp_mail_apply"])
    return ""


def _provider_routing_base_lookup(guide: dict[str, Any], aliases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _normalize_provider_name(item.get("provider")): item
        for item in (guide.get("providers") or [])
        if isinstance(item, dict) and _normalize_provider_name(item.get("provider"))
    }


def _provider_routing_row(
    raw_provider: Any,
    *,
    scope_name: str,
    scope: dict[str, Any],
    provider_entries: dict[str, dict[str, Any]],
    aliases: dict[str, Any],
    endpoints: dict[str, str],
) -> dict[str, Any]:
    provider = _normalize_provider_name(raw_provider)
    entry = provider_entries.get(provider)
    canonical_provider = _provider_recipe_alias_canonical(provider, aliases) or (
        _canonical_bridge_operator_provider(provider)
        if provider in _BRIDGE_OPERATOR_FAMILY and provider != _BRIDGE_OPERATOR_CANONICAL
        else None
    )
    if not isinstance(entry, dict) and canonical_provider:
        entry = provider_entries.get(canonical_provider)
    if not isinstance(entry, dict) and provider in _BRIDGE_OPERATOR_FAMILY:
        entry = provider_entries.get(_BRIDGE_OPERATOR_CANONICAL) or {}
        canonical_provider = canonical_provider or _BRIDGE_OPERATOR_CANONICAL
    entry = entry if isinstance(entry, dict) else {}
    provider_examples = {
        _normalize_provider_name(item.get("provider")): {
            "kind": item.get("kind"),
            "label": item.get("label"),
            "active": item.get("active", True),
        }
        for item in (provider_entries.values())
        if isinstance(item, dict) and _normalize_provider_name(item.get("provider"))
    }
    alias_info = (
        (aliases.get("pool_claim_provider_aliases") or {}).get(provider)
        if isinstance(aliases.get("pool_claim_provider_aliases"), dict)
        else {}
    )
    is_auto = provider == "auto"
    is_pool_alias = isinstance(alias_info, dict) and bool(alias_info)
    active = True if is_auto else bool(entry.get("active", _provider_recipe_active(provider, provider_examples, aliases)))
    configured = True if is_auto else bool(entry.get("configured", False if not entry else True))
    status = (
        "ready"
        if is_auto
        else str(
            entry.get("readiness_status")
            or ("ready" if active and configured else "inactive" if not active else "needs_config")
        )
    )
    usable = bool(is_auto or (active and configured))
    if is_auto:
        reason = "automatic_provider_selection"
        kind = "auto"
        label = "Auto"
    elif is_pool_alias:
        reason = "alias_pool_claim_provider"
        kind = (
            "account"
            if str(alias_info.get("kind") or "") == "account"
            else _provider_recipe_kind(provider, provider_examples, aliases)
        )
        label = _provider_recipe_label(provider, provider_examples, aliases)
        active = True
        configured = True if not entry else configured
        usable = True if not entry else usable
        status = "ready" if not entry else status
    elif canonical_provider and provider not in provider_entries:
        reason = "alias_runtime_temp_provider"
        kind = _provider_recipe_kind(provider, provider_examples, aliases)
        label = _provider_recipe_label(provider, provider_examples, aliases)
    elif not active:
        reason = "not_in_active_allowlist"
        kind = str(entry.get("kind") or _provider_recipe_kind(provider, provider_examples, aliases))
        label = str(entry.get("label") or _provider_recipe_label(provider, provider_examples, aliases))
    elif not configured:
        reason = "missing_config"
        kind = str(entry.get("kind") or _provider_recipe_kind(provider, provider_examples, aliases))
        label = str(entry.get("label") or _provider_recipe_label(provider, provider_examples, aliases))
    else:
        reason = "local_config_ready"
        kind = str(entry.get("kind") or _provider_recipe_kind(provider, provider_examples, aliases))
        label = str(entry.get("label") or _provider_recipe_label(provider, provider_examples, aliases))
    endpoint = _provider_routing_endpoint_for_scope(scope_name, scope, endpoints)
    return {
        "provider": provider,
        "canonical_provider": canonical_provider or (str(entry.get("provider") or provider) if entry else provider),
        "label": label or provider,
        "kind": kind or "unknown",
        "active": active,
        "configured": configured,
        "usable": usable,
        "status": status,
        "reason": reason,
        "aliases": _provider_routing_aliases(provider, aliases),
        "endpoints": {
            "request": endpoint,
            "health": str(
                (entry.get("health") or {}).get("endpoint") or endpoints.get("provider_health") or PROVIDER_HEALTH_ENDPOINT
            ),
            "mailboxes": str(
                (entry.get("endpoints") or {}).get("mailboxes")
                or endpoints.get("mailboxes")
                or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]
            ),
        },
    }


def _provider_routing_scope(
    scope_name: str,
    *,
    selection_policy: dict[str, Any],
    provider_integration_guide: dict[str, Any],
) -> dict[str, Any]:
    scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    scope = scopes.get(scope_name) if isinstance(scopes.get(scope_name), dict) else {}
    endpoints = _provider_integration_endpoint_map(
        provider_integration_guide.get("endpoints") if isinstance(provider_integration_guide.get("endpoints"), dict) else None
    )
    aliases = (
        provider_integration_guide.get("aliases")
        if isinstance(provider_integration_guide.get("aliases"), dict)
        else get_provider_alias_contract()
    )
    provider_entries = _provider_routing_base_lookup(provider_integration_guide, aliases)
    allowed_values = [
        _normalize_provider_name(item) for item in (scope.get("allowed_values") or []) if _normalize_provider_name(item)
    ]
    rows = [
        _provider_routing_row(
            provider,
            scope_name=scope_name,
            scope=scope,
            provider_entries=provider_entries,
            aliases=aliases,
            endpoints=endpoints,
        )
        for provider in allowed_values
    ]
    return {
        "scope": scope_name,
        "label": _PROVIDER_ROUTING_SCOPE_LABELS.get(scope_name, scope_name),
        "request_field": str(scope.get("request_field") or ""),
        "settings_key": str(scope.get("settings_key") or ""),
        "env": str(scope.get("env") or ""),
        "endpoint": _provider_routing_endpoint_for_scope(scope_name, scope, endpoints),
        "allowed_values": allowed_values,
        "counts": {
            "total": len(rows),
            "usable": sum(1 for row in rows if row.get("usable")),
            "needs_config": sum(1 for row in rows if row.get("status") == "needs_config"),
            "inactive": sum(1 for row in rows if row.get("status") == "inactive"),
        },
        "providers": rows,
    }


def _provider_routing_matrix(
    *,
    selection_policy: dict[str, Any],
    provider_integration_guide: dict[str, Any],
) -> dict[str, Any]:
    scope_names = ["temp_runtime_default", "task_temp_apply", "pool_claim_default", "explicit_pool_claim"]
    scopes = {
        scope_name: _provider_routing_scope(
            scope_name,
            selection_policy=selection_policy,
            provider_integration_guide=provider_integration_guide,
        )
        for scope_name in scope_names
    }
    return {
        "version": 1,
        "source_priority": list(selection_policy.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY),
        "scopes": scopes,
    }


def _provider_capability_aliases(provider: str, aliases: dict[str, Any]) -> list[str]:
    values = _provider_routing_aliases(provider, aliases)
    pool_aliases = (
        aliases.get("pool_claim_provider_aliases") if isinstance(aliases.get("pool_claim_provider_aliases"), dict) else {}
    )
    for key, raw_info in pool_aliases.items():
        info = raw_info if isinstance(raw_info, dict) else {}
        canonical = _normalize_provider_name(info.get("canonical_provider"))
        if canonical == provider:
            _append_unique(values, [key])
    return sorted(set(values))


def _provider_capability_selection_fields(*, kind: str, provider: str, selection_policy: dict[str, Any]) -> dict[str, Any]:
    scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    result: dict[str, Any] = {}
    pool_scope = scopes.get("explicit_pool_claim") if isinstance(scopes.get("explicit_pool_claim"), dict) else {}
    task_scope = scopes.get("task_temp_apply") if isinstance(scopes.get("task_temp_apply"), dict) else {}
    if kind == "account":
        result["pool_claim"] = {
            "field": str(pool_scope.get("request_field") or "provider"),
            "value": provider,
        }
    if kind == "temp":
        result["task_temp_apply"] = {
            "field": str(task_scope.get("request_field") or "provider_name"),
            "value": provider,
        }
        result["pool_claim"] = {
            "field": str(pool_scope.get("request_field") or "provider"),
            "value": provider,
        }
    return result


def _provider_capability_lifecycle_actions(*, kind: str) -> list[str]:
    if kind == "account":
        return ["claim_pool_mailbox", "read_session", "complete_claim", "release_claim", "close_mailbox_session"]
    if kind == "temp":
        return ["apply_task_mailbox", "read_session", "finish_task_mailbox", "close_mailbox_session"]
    return ["read_session"]


def _provider_capability_row(
    row: dict[str, Any],
    *,
    selection_policy: dict[str, Any],
    aliases: dict[str, Any],
    endpoints: dict[str, str],
    workflow_provider_sets: dict[str, set[str]],
) -> dict[str, Any]:
    kind = str(row.get("kind") or "").strip().lower()
    provider = _normalize_provider_name(row.get("provider"))
    can_dynamic_create = bool(row.get("can_dynamic_create"))
    requires_pool_inventory = bool(row.get("requires_pool_inventory"))
    task_temp_capable = provider in workflow_provider_sets.get("task_temp_mailbox", set())
    pool_claim_capable = provider in workflow_provider_sets.get("pool_claim", set())
    session_capable = bool(pool_claim_capable or task_temp_capable)
    directory_visible = kind in {"account", "temp"}
    read_capability = str(row.get("read_capability") or "").strip().lower()
    read_capabilities = list(row.get("read_capabilities") or [])
    if read_capability and read_capability not in read_capabilities:
        read_capabilities.append(read_capability)
    workflow_support = {
        "mailbox_session": session_capable,
        "pool_claim": pool_claim_capable,
        "task_temp_mailbox": task_temp_capable,
        "mailbox_directory": directory_visible,
        "provider_health": True,
    }
    return {
        "kind": kind,
        "provider": provider,
        "label": str(row.get("label") or provider),
        "active": bool(row.get("active", True)),
        "configured": bool(row.get("configured", True)),
        "readiness_status": str(row.get("readiness_status") or "unknown"),
        "config_source": str(row.get("config_source") or "catalog"),
        "aliases": _provider_capability_aliases(provider, aliases),
        "capabilities": {
            "can_dynamic_create": can_dynamic_create,
            "requires_pool_inventory": requires_pool_inventory,
            "session_capable": session_capable,
            "pool_claim_capable": pool_claim_capable,
            "task_temp_capable": task_temp_capable,
            "directory_visible": directory_visible,
            "provider_health": True,
        },
        "read": {
            "capability": read_capability,
            "capabilities": read_capabilities,
            "actions": list(_PROVIDER_CAPABILITY_READ_ACTIONS),
        },
        "lifecycle_actions": _provider_capability_lifecycle_actions(kind=kind),
        "workflow_support": workflow_support,
        "selection_fields": _provider_capability_selection_fields(
            kind=kind, provider=provider, selection_policy=selection_policy
        ),
        "configuration": {
            "missing_config_count": int(row.get("missing_config_count") or 0),
            "needs_config": str(row.get("readiness_status") or "") == "needs_config",
        },
        "inventory": {
            "mailbox_count": int(row.get("mailbox_count") or 0),
            "account_count": int(row.get("account_count") or 0),
            "temp_count": int(row.get("temp_count") or 0),
        },
        "endpoints": {
            "mailboxes": str(
                (row.get("endpoints") or {}).get("mailboxes")
                or endpoints.get("mailboxes")
                or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]
            ),
            "provider_health": str(
                (row.get("endpoints") or {}).get("health") or endpoints.get("provider_health") or PROVIDER_HEALTH_ENDPOINT
            ),
            "mailbox_session_start": str(
                endpoints.get("mailbox_session_start") or _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_start"]
            ),
            "mailbox_session_read": str(
                endpoints.get("mailbox_session_read") or _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_read"]
            ),
            "mailbox_session_close": str(
                endpoints.get("mailbox_session_close") or _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_close"]
            ),
        },
    }


def _provider_capability_workflow(
    workflow: str, rows: list[dict[str, Any]], selection_policy: dict[str, Any]
) -> dict[str, Any]:
    providers = [str(row.get("provider") or "") for row in rows if (row.get("workflow_support") or {}).get(workflow)]
    selector_fields = {
        "pool_claim": (
            str(((selection_policy.get("scopes") or {}).get("explicit_pool_claim") or {}).get("request_field") or "provider")
            if isinstance(selection_policy.get("scopes"), dict)
            else "provider"
        ),
        "task_temp_apply": (
            str(((selection_policy.get("scopes") or {}).get("task_temp_apply") or {}).get("request_field") or "provider_name")
            if isinstance(selection_policy.get("scopes"), dict)
            else "provider_name"
        ),
    }
    return {
        "workflow": workflow,
        "label": _PROVIDER_CAPABILITY_WORKFLOWS.get(workflow, workflow),
        "provider_count": len(providers),
        "providers": providers,
        "selector_fields": selector_fields,
    }


def _provider_capability_workflow_provider_sets(routing_matrix: dict[str, Any]) -> dict[str, set[str]]:
    scopes = routing_matrix.get("scopes") if isinstance(routing_matrix.get("scopes"), dict) else {}
    result: dict[str, set[str]] = {
        "pool_claim": set(),
        "task_temp_mailbox": set(),
    }
    scope_map = {
        "pool_claim": "explicit_pool_claim",
        "task_temp_mailbox": "task_temp_apply",
    }
    for workflow, scope_name in scope_map.items():
        scope = scopes.get(scope_name) if isinstance(scopes.get(scope_name), dict) else {}
        for item in scope.get("providers") or []:
            if not isinstance(item, dict):
                continue
            provider = _normalize_provider_name(item.get("provider"))
            canonical = _normalize_provider_name(item.get("canonical_provider"))
            if provider and provider != "auto":
                result[workflow].add(provider)
            if canonical and canonical != "auto":
                result[workflow].add(canonical)
    return result


def _provider_capability_matrix(
    *,
    readiness_rows: list[dict[str, Any]],
    selection_policy: dict[str, Any],
    provider_integration_guide: dict[str, Any],
) -> dict[str, Any]:
    endpoints = _provider_integration_endpoint_map(
        provider_integration_guide.get("endpoints") if isinstance(provider_integration_guide.get("endpoints"), dict) else None
    )
    aliases = (
        provider_integration_guide.get("aliases")
        if isinstance(provider_integration_guide.get("aliases"), dict)
        else get_provider_alias_contract()
    )
    routing_matrix = _provider_routing_matrix(
        selection_policy=selection_policy, provider_integration_guide=provider_integration_guide
    )
    workflow_provider_sets = _provider_capability_workflow_provider_sets(routing_matrix)
    rows = [
        _provider_capability_row(
            row,
            selection_policy=selection_policy,
            aliases=aliases,
            endpoints=endpoints,
            workflow_provider_sets=workflow_provider_sets,
        )
        for row in readiness_rows
        if str(row.get("kind") or "").strip().lower() in {"account", "temp"} and _normalize_provider_name(row.get("provider"))
    ]
    rows = sorted(
        rows,
        key=lambda item: (str(item.get("kind") or ""), str(item.get("label") or "").lower(), str(item.get("provider") or "")),
    )
    workflows = {
        workflow: _provider_capability_workflow(workflow, rows, selection_policy)
        for workflow in _PROVIDER_CAPABILITY_WORKFLOWS
    }
    totals = {
        "providers": len(rows),
        "account_providers": sum(1 for row in rows if row.get("kind") == "account"),
        "temp_providers": sum(1 for row in rows if row.get("kind") == "temp"),
        "dynamic_create_providers": sum(1 for row in rows if (row.get("capabilities") or {}).get("can_dynamic_create")),
        "pool_inventory_providers": sum(1 for row in rows if (row.get("capabilities") or {}).get("requires_pool_inventory")),
        "task_temp_capable_providers": sum(1 for row in rows if (row.get("capabilities") or {}).get("task_temp_capable")),
        "pool_claim_capable_providers": sum(1 for row in rows if (row.get("capabilities") or {}).get("pool_claim_capable")),
        "session_capable_providers": sum(1 for row in rows if (row.get("capabilities") or {}).get("session_capable")),
        "needs_config_providers": sum(1 for row in rows if (row.get("configuration") or {}).get("needs_config")),
    }
    return {
        "version": 1,
        "generated_from": ["provider_catalog", "provider_integration_guide", "provider_routing_matrix"],
        "totals": totals,
        "workflows": workflows,
        "providers": rows,
    }


def get_mailbox_provider_readiness_summary(
    *,
    mailbox_inventory: dict[str, Any] | None = None,
    provider_diagnostics: dict[str, Any] | None = None,
    provider_integration_guide: dict[str, Any] | None = None,
    selection_policy: dict[str, Any] | None = None,
    discovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project provider readiness and mailbox inventory into one secret-free summary."""
    diagnostics = provider_diagnostics if isinstance(provider_diagnostics, dict) else {}
    diagnostic_summary = diagnostics.get("summary") if isinstance(diagnostics.get("summary"), dict) else {}
    guide = provider_integration_guide if isinstance(provider_integration_guide, dict) else {}
    if isinstance(selection_policy, dict) and selection_policy.get("scopes"):
        policy = selection_policy
    else:
        deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
        policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    scopes = policy.get("scopes") if isinstance(policy.get("scopes"), dict) else {}
    endpoints = _provider_integration_endpoint_map(
        guide.get("endpoints") if isinstance(guide.get("endpoints"), dict) else None
    )
    discovery = discovery if isinstance(discovery, dict) else {}
    inventory_rows = _mailbox_inventory_rows(mailbox_inventory)
    provider_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for guide_provider in guide.get("providers") or []:
        if not isinstance(guide_provider, dict):
            continue
        kind = str(guide_provider.get("kind") or "").strip().lower()
        provider = _normalize_provider_name(guide_provider.get("provider"))
        if not kind or not provider:
            continue
        key = (kind, provider)
        provider_rows[key] = _mailbox_readiness_provider_row(guide_provider, inventory_rows.get(key))
    for key, inventory in inventory_rows.items():
        if key in provider_rows:
            continue
        provider_rows[key] = _mailbox_readiness_provider_row(
            {
                "kind": inventory.get("kind"),
                "provider": inventory.get("provider"),
                "label": inventory.get("label"),
                "active": True,
                "configured": True,
                "readiness_status": "inventory_only",
                "capabilities": {},
                "endpoints": endpoints,
            },
            inventory,
        )
    rows = sorted(
        provider_rows.values(),
        key=lambda row: (str(row.get("kind") or ""), str(row.get("label") or "").lower(), str(row.get("provider") or "")),
    )
    inventory_totals = _mailbox_inventory_totals(mailbox_inventory, inventory_rows)
    active_count = int(diagnostic_summary.get("active") or sum(1 for row in rows if row.get("active")))
    ready_count = int(diagnostic_summary.get("ready") or sum(1 for row in rows if row.get("active") and row.get("configured")))
    needs_config_count = int(
        diagnostic_summary.get("needs_config") or sum(1 for row in rows if row.get("active") and not row.get("configured"))
    )
    inactive_count = int(diagnostic_summary.get("inactive") or sum(1 for row in rows if not row.get("active")))
    configured_count = int(diagnostic_summary.get("configured") or sum(1 for row in rows if row.get("configured")))
    dynamic_create_count = int(
        diagnostic_summary.get("dynamic_create") or sum(1 for row in rows if row.get("can_dynamic_create"))
    )
    issues = {
        "needs_config": needs_config_count,
        "inactive": inactive_count,
        "unknown_filter_entries": int(diagnostic_summary.get("unknown_filter_entries") or 0),
        "invalid_default_entries": int(diagnostic_summary.get("invalid_default_entries") or 0),
        "inactive_default_entries": int(diagnostic_summary.get("inactive_default_entries") or 0),
    }
    overall_status = "ready"
    if issues["unknown_filter_entries"] > 0 or issues["invalid_default_entries"] > 0:
        overall_status = "degraded"
    elif needs_config_count > 0 or active_count <= 0:
        overall_status = "needs_config"
    totals = {
        **inventory_totals,
        "providers": len(rows),
        "active_providers": active_count,
        "ready_providers": ready_count,
        "configured_providers": configured_count,
        "needs_config_providers": needs_config_count,
        "dynamic_create_providers": dynamic_create_count,
        "account_providers": int(diagnostic_summary.get("account") or sum(1 for row in rows if row.get("kind") == "account")),
        "temp_providers": int(diagnostic_summary.get("temp") or sum(1 for row in rows if row.get("kind") == "temp")),
    }
    return {
        "version": 1,
        "overall_status": overall_status,
        "totals": totals,
        "issues": issues,
        "source_priority": list(
            policy.get("source_priority") or guide.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY
        ),
        "provider_selector_fields": {
            "pool_claim": str((scopes.get("explicit_pool_claim") or {}).get("request_field") or "provider"),
            "task_temp_apply": str((scopes.get("task_temp_apply") or {}).get("request_field") or "provider_name"),
        },
        "routing_matrix": _provider_routing_matrix(selection_policy=policy, provider_integration_guide=guide),
        "capability_matrix": _provider_capability_matrix(
            readiness_rows=rows,
            selection_policy=policy,
            provider_integration_guide=guide,
        ),
        "endpoints": {
            "mailboxes": str(endpoints.get("mailboxes") or _CANONICAL_EXTERNAL_ENDPOINTS["mailboxes"]),
            "providers": str(
                discovery.get("providers_endpoint") or endpoints.get("providers") or _CANONICAL_EXTERNAL_ENDPOINTS["providers"]
            ),
            "provider_health": str(
                discovery.get("provider_health_endpoint") or endpoints.get("provider_health") or PROVIDER_HEALTH_ENDPOINT
            ),
            "provider_preflight": str(
                discovery.get("provider_preflight_endpoint")
                or endpoints.get("provider_preflight")
                or PROVIDER_PREFLIGHT_ENDPOINT
            ),
        },
        "providers": rows,
    }


def _integration_manifest_key_hints(
    keys: Any,
    *,
    required_keys: Any,
    secret_keys: Any,
    defaults: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    defaults = defaults if isinstance(defaults, dict) else {}
    required = {str(item or "").strip() for item in (required_keys or []) if str(item or "").strip()}
    secret = {str(item or "").strip() for item in (secret_keys or []) if str(item or "").strip()}
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_key in keys or []:
        key = str(raw_key or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        is_secret = key in secret
        entry: dict[str, Any] = {
            "key": key,
            "required": key in required,
            "secret": is_secret,
            "value": "" if is_secret else copy.deepcopy(defaults.get(key, "")),
        }
        if key in defaults and not is_secret:
            entry["default"] = copy.deepcopy(defaults[key])
        result.append(entry)
    return result


def _integration_manifest_provider_entry(provider_entry: dict[str, Any]) -> dict[str, Any]:
    configuration = provider_entry.get("configuration") if isinstance(provider_entry.get("configuration"), dict) else {}
    required_env = list(provider_entry.get("required_env") or configuration.get("required_env") or [])
    optional_env = list(provider_entry.get("optional_env") or configuration.get("optional_env") or [])
    env_keys: list[str] = []
    _append_unique(env_keys, required_env)
    _append_unique(env_keys, optional_env)

    required_settings = list(provider_entry.get("required_settings") or configuration.get("required_settings") or [])
    settings_keys: list[str] = []
    _append_unique(settings_keys, provider_entry.get("settings_keys") or configuration.get("settings_keys") or [])
    _append_unique(settings_keys, required_settings)

    request_fields: dict[str, Any] = {}
    endpoints = provider_entry.get("endpoints") if isinstance(provider_entry.get("endpoints"), dict) else {}
    pool_claim_request = (
        provider_entry.get("pool_claim_request") if isinstance(provider_entry.get("pool_claim_request"), dict) else {}
    )
    if pool_claim_request.get("field"):
        request_fields["pool_claim"] = {
            "request_field": pool_claim_request.get("field"),
            "value": copy.deepcopy(pool_claim_request.get("value")),
            "endpoint": pool_claim_request.get("endpoint") or endpoints.get("pool_claim_random"),
            "body_fields": list(pool_claim_request.get("body_fields") or []),
        }
    task_temp_apply_request = (
        provider_entry.get("task_temp_apply_request")
        if isinstance(provider_entry.get("task_temp_apply_request"), dict)
        else {}
    )
    if task_temp_apply_request.get("field"):
        request_fields["task_temp_apply"] = {
            "request_field": task_temp_apply_request.get("field"),
            "value": copy.deepcopy(task_temp_apply_request.get("value")),
            "endpoint": task_temp_apply_request.get("endpoint") or endpoints.get("temp_mail_apply"),
            "body_fields": list(task_temp_apply_request.get("body_fields") or []),
        }

    config_file_examples: dict[str, Any] = {}
    for step_name in ("activation", "runtime_default", "pool_claim_default"):
        step = provider_entry.get(step_name) if isinstance(provider_entry.get(step_name), dict) else {}
        provider_config = step.get("provider_config") if isinstance(step.get("provider_config"), dict) else {}
        if provider_config:
            config_file_examples[step_name] = copy.deepcopy(provider_config)

    return {
        "provider": provider_entry.get("provider") or "",
        "label": provider_entry.get("label") or provider_entry.get("provider") or "",
        "kind": provider_entry.get("kind") or "",
        "active": bool(provider_entry.get("active")),
        "configured": bool(provider_entry.get("configured")),
        "readiness_status": provider_entry.get("readiness_status") or "",
        "readiness_reason": provider_entry.get("readiness_reason") or "",
        "required_env": required_env,
        "optional_env": optional_env,
        "settings_keys": settings_keys,
        "required_settings": required_settings,
        "secret_env": list(provider_entry.get("secret_env") or configuration.get("secret_env") or []),
        "secret_settings": list(provider_entry.get("secret_settings") or configuration.get("secret_settings") or []),
        "env": _integration_manifest_key_hints(
            env_keys,
            required_keys=required_env,
            secret_keys=provider_entry.get("secret_env") or configuration.get("secret_env") or [],
            defaults=configuration.get("env_defaults") or {},
        ),
        "settings": _integration_manifest_key_hints(
            settings_keys,
            required_keys=required_settings,
            secret_keys=provider_entry.get("secret_settings") or configuration.get("secret_settings") or [],
            defaults=configuration.get("settings_defaults") or {},
        ),
        "request_fields": request_fields,
        "config_file_examples": config_file_examples,
        "aliases": copy.deepcopy(provider_entry.get("aliases") or {}),
        "capabilities": copy.deepcopy(provider_entry.get("capabilities") or {}),
        "contract_validation": copy.deepcopy(provider_entry.get("contract_validation") or {}),
        "endpoints": copy.deepcopy(endpoints),
        "health": copy.deepcopy(provider_entry.get("health") or {}),
        "mailbox_directory_filter": copy.deepcopy(provider_entry.get("mailbox_directory_filter") or {}),
    }


def _integration_manifest_provider_selector(scope: dict[str, Any], *, source: str, default_field: str) -> dict[str, Any]:
    return {
        "field": str(scope.get("request_field") or default_field).strip() or default_field,
        "allowed_values": list(scope.get("allowed_values") or []),
        "optional": True,
        "source": source,
    }


def _integration_manifest_quickstart(
    *,
    endpoints: dict[str, str],
    selection_policy: dict[str, Any],
) -> dict[str, Any]:
    selection_scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    pool_scope = (
        selection_scopes.get("explicit_pool_claim") if isinstance(selection_scopes.get("explicit_pool_claim"), dict) else {}
    )
    task_scope = selection_scopes.get("task_temp_apply") if isinstance(selection_scopes.get("task_temp_apply"), dict) else {}
    pool_provider_field = str(pool_scope.get("request_field") or "provider").strip() or "provider"
    task_provider_field = str(task_scope.get("request_field") or "provider_name").strip() or "provider_name"

    pool_claim_body = {
        "caller_id": "<caller-id>",
        "task_id": "<task-id>",
        pool_provider_field: "<provider-or-auto>",
        "email_domain": "",
        "project_key": "",
    }
    task_apply_body = {
        "caller_id": "<caller-id>",
        "task_id": "<task-id>",
        task_provider_field: "<provider-name>",
        "prefix": "",
        "domain": "",
    }

    return {
        "version": 1,
        "auth": {
            "scheme": "api_key",
            "header": "X-API-Key",
            "placeholder": "<your-api-key>",
            "headers": {"X-API-Key": "<your-api-key>"},
            "curl_header": "X-API-Key: <your-api-key>",
        },
        "recommended_sequence": [
            {
                "step": "capabilities",
                "method": "GET",
                "endpoint": endpoints["capabilities"],
                "response_field": "quickstart",
            },
            {
                "step": "providers",
                "method": "GET",
                "endpoint": endpoints["providers"],
                "response_field": "quickstart",
            },
            {
                "step": "mailboxes",
                "method": "GET",
                "endpoint": endpoints["mailboxes"],
                "query": {"kind": "all", "provider": "all", "sort": "updated_desc"},
            },
        ],
        "provider_selector_fields": {
            "pool_claim": _integration_manifest_provider_selector(
                pool_scope,
                source="selection_policy.scopes.explicit_pool_claim",
                default_field="provider",
            ),
            "task_temp_apply": _integration_manifest_provider_selector(
                task_scope,
                source="selection_policy.scopes.task_temp_apply",
                default_field="provider_name",
            ),
        },
        "endpoints": {
            "capabilities": endpoints["capabilities"],
            "integration_bundle": endpoints["integration_bundle"],
            "openapi": str(endpoints.get("openapi") or _CANONICAL_EXTERNAL_ENDPOINTS["openapi"]),
            "providers": endpoints["providers"],
            "provider_preflight": endpoints["provider_preflight"],
            "mailboxes": endpoints["mailboxes"],
            "mailbox_session_start": endpoints["mailbox_session_start"],
            "mailbox_session_read": endpoints["mailbox_session_read"],
            "mailbox_session_close": endpoints["mailbox_session_close"],
            "pool_claim_random": endpoints["pool_claim_random"],
            "temp_mail_apply": endpoints["temp_mail_apply"],
            "messages": endpoints["messages"],
            "verification_code": endpoints["verification_code"],
        },
        "requests": {
            "mailbox_directory": {
                "method": "GET",
                "endpoint": endpoints["mailboxes"],
                "query": {"kind": "all", "provider": "all", "sort": "updated_desc"},
            },
            "provider_preflight": {
                "method": "GET",
                "endpoint": endpoints["provider_preflight"],
                "query": {"probe_network": False},
            },
            "integration_bundle": {
                "method": "GET",
                "endpoint": endpoints["integration_bundle"],
            },
            "pool_claim": {
                "method": "POST",
                "endpoint": endpoints["pool_claim_random"],
                "body": pool_claim_body,
            },
            "task_temp_apply": {
                "method": "POST",
                "endpoint": endpoints["temp_mail_apply"],
                "body": task_apply_body,
            },
            "mailbox_session_start": {
                "method": "POST",
                "endpoint": endpoints["mailbox_session_start"],
                "body": {
                    "caller_id": "<caller-id>",
                    "task_id": "<task-id>",
                    "source_strategy": "pool_first",
                    "provider": "<provider-or-auto>",
                    "provider_name": "<provider-name>",
                    "email_domain": "",
                    "project_key": "",
                    "prefix": "",
                    "domain": "",
                },
            },
            "mailbox_session_read": {
                "method": "POST",
                "endpoint": endpoints["mailbox_session_read"],
                "body": {
                    "session_type": "<session-type-from-start-response>",
                    "read_action": "verification_code",
                    "caller_id": "<caller-id>",
                    "task_id": "<task-id>",
                    "email": "<email-from-start-response>",
                    "claim_token": "<pool-claim-token-from-lifecycle>",
                    "task_token": "<task-token-from-lifecycle>",
                    "since_minutes": 10,
                },
            },
            "mailbox_session_close": {
                "method": "POST",
                "endpoint": endpoints["mailbox_session_close"],
                "body": {
                    "session_type": "<session-type-from-start-response>",
                    "account_id": "<pool-account-id-from-lifecycle>",
                    "claim_token": "<pool-claim-token-from-lifecycle>",
                    "task_token": "<task-token-from-lifecycle>",
                    "caller_id": "<caller-id>",
                    "task_id": "<task-id>",
                    "result": "success",
                    "detail": "",
                },
            },
            "read_messages": {
                "method": "GET",
                "endpoint": endpoints["messages"],
                "query": {"email": "<email>"},
            },
            "read_verification_code": {
                "method": "GET",
                "endpoint": endpoints["verification_code"],
                "query": {"email": "<email>"},
            },
        },
        "workflow_keys": {
            "browse_mailbox_directory": "browse_mailbox_directory",
            "start_mailbox_session": "start_mailbox_session",
            "close_mailbox_session": "start_mailbox_session.close_session",
            "claim_pool_mailbox": "claim_pool_mailbox",
            "create_task_temp_mailbox": "create_task_temp_mailbox",
        },
    }


def _integration_manifest_action_step(
    key: str,
    action: dict[str, Any],
    *,
    label: str,
    description: str,
    response_field: str = "data",
    next_action: str = "",
) -> dict[str, Any]:
    step: dict[str, Any] = {
        "key": key,
        "label": label,
        "description": description,
        "method": str(action.get("method") or "GET").upper(),
        "endpoint": str(action.get("endpoint") or ""),
        "auth": "api_key",
        "request": {},
        "response": {"field": response_field},
    }
    request: dict[str, Any] = step["request"]
    for field_name in ("path_fields", "query_fields", "body_fields", "fixed_query"):
        if field_name in action:
            request[field_name] = copy.deepcopy(action.get(field_name))
    if not request:
        step.pop("request", None)
    if next_action:
        step["next"] = {"success": next_action}
    return step


def _integration_manifest_workflows(
    *,
    endpoints: dict[str, str],
    selection_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    selection_scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    pool_scope = (
        selection_scopes.get("explicit_pool_claim") if isinstance(selection_scopes.get("explicit_pool_claim"), dict) else {}
    )
    task_scope = selection_scopes.get("task_temp_apply") if isinstance(selection_scopes.get("task_temp_apply"), dict) else {}
    pool_provider_field = str(pool_scope.get("request_field") or "provider").strip() or "provider"
    task_provider_field = str(task_scope.get("request_field") or "provider_name").strip() or "provider_name"
    directory_read_actions = _action_contract_next_actions_for_endpoint_map(lifecycle="none", endpoints=endpoints)
    pool_read_actions = _action_contract_next_actions_for_endpoint_map(lifecycle="pool_claim", endpoints=endpoints)
    task_read_actions = _action_contract_next_actions_for_endpoint_map(lifecycle="task_temp_mailbox", endpoints=endpoints)
    session_read_action = copy.deepcopy(
        pool_read_actions.get("read_session") or _EXTERNAL_MAILBOX_SESSION_READ_ACTION["read_session"]
    )
    session_close_action = copy.deepcopy(
        pool_read_actions.get("close_session") or _EXTERNAL_MAILBOX_SESSION_CLOSE_ACTION["close_session"]
    )

    pool_claim_body_fields = ["caller_id", "task_id", pool_provider_field, "email_domain", "project_key"]
    task_apply_body_fields = ["caller_id", "task_id", "prefix", "domain", task_provider_field]

    return [
        {
            "key": "start_mailbox_session",
            "label": "Start mailbox session",
            "description": "Create a readable mailbox session through one provider-neutral entry point, using pool or task temp-mail lifecycle based on source_strategy.",
            "steps": [
                {
                    "key": "start_session",
                    "label": "Start session",
                    "description": "Start a mailbox session and receive lifecycle handles plus read actions.",
                    "method": "POST",
                    "endpoint": endpoints["mailbox_session_start"],
                    "auth": "api_key",
                    "request": {
                        "body_fields": [
                            "caller_id",
                            "task_id",
                            "source_strategy",
                            pool_provider_field,
                            task_provider_field,
                            "email_domain",
                            "project_key",
                            "prefix",
                            "domain",
                        ],
                        "required_body_fields": ["caller_id", "task_id"],
                        "source_strategy_values": ["pool_first", "task_temp_first", "pool_only", "task_temp_only"],
                    },
                    "response": {
                        "field": "data",
                        "session_type_field": "session_type",
                        "email_field": "email",
                        "lifecycle_field": "lifecycle",
                        "action_contract_field": "external_mailbox_read_contract",
                    },
                    "next": {"success": "read_session"},
                },
                _integration_manifest_action_step(
                    "read_session",
                    session_read_action,
                    label="Read session mailbox",
                    description="Read messages or verification data from the started mailbox session without branching on pool versus task temp-mail lifecycle.",
                    response_field="data.result",
                    next_action="close_session",
                ),
                _integration_manifest_action_step(
                    "close_session",
                    session_close_action,
                    label="Close session",
                    description="Close the started pool claim or task temp-mailbox through the unified session close endpoint.",
                    response_field="data",
                ),
            ],
        },
        {
            "key": "discover_external_api",
            "label": "Discover external API",
            "description": "Fetch the machine-readable capabilities, provider catalog, and mailbox directory contracts before choosing a mailbox source.",
            "steps": [
                {
                    "key": "capabilities",
                    "label": "Read capabilities",
                    "description": "Load the top-level external API contract and manifest.",
                    "method": "GET",
                    "endpoint": endpoints["capabilities"],
                    "auth": "api_key",
                    "response": {"field": "integration_manifest"},
                    "next": {"success": "providers"},
                },
                {
                    "key": "providers",
                    "label": "Read providers",
                    "description": "Load provider readiness, selection policy, deployment hints, and per-provider request fields.",
                    "method": "GET",
                    "endpoint": endpoints["providers"],
                    "auth": "api_key",
                    "response": {"field": "integration_manifest.providers"},
                    "next": {"success": "mailboxes"},
                },
                {
                    "key": "mailboxes",
                    "label": "Read mailbox directory",
                    "description": "List the unified mailbox directory using provider-neutral filters.",
                    "method": "GET",
                    "endpoint": endpoints["mailboxes"],
                    "auth": "api_key",
                    "request": {"query": {"kind": "all", "provider": "all", "sort": "updated_desc"}},
                    "response": {
                        "field": "mailboxes",
                        "context_field": "provider_context",
                        "action_contract_field": "action_contract",
                    },
                },
            ],
        },
        {
            "key": "browse_mailbox_directory",
            "label": "Browse mailbox directory",
            "description": "Use the unified directory to inspect account and temp mailboxes before reading messages.",
            "steps": [
                {
                    "key": "list_mailboxes",
                    "label": "List mailboxes",
                    "description": "Filter by kind, status, action, provider, search, sort, and pagination fields from the directory contract.",
                    "method": "GET",
                    "endpoint": endpoints["mailboxes"],
                    "auth": "api_key",
                    "request": {
                        "query_fields": [
                            "kind",
                            "status",
                            "read_capability",
                            "action",
                            "provider",
                            "search",
                            "sort",
                            "page",
                            "page_size",
                        ]
                    },
                    "response": {
                        "field": "mailboxes",
                        "context_field": "provider_context",
                        "action_contract_field": "action_contract",
                    },
                    "next": {"success": "read_messages"},
                },
                _integration_manifest_action_step(
                    "read_messages",
                    directory_read_actions.get("read_messages") or {},
                    label="Read messages",
                    description="Read messages for the selected mailbox by email or claim token.",
                    response_field="emails",
                ),
                _integration_manifest_action_step(
                    "read_verification_code",
                    directory_read_actions.get("read_verification_code") or {},
                    label="Read verification code",
                    description="Extract a verification code from the selected mailbox.",
                    response_field="verification_code",
                ),
            ],
        },
        {
            "key": "claim_pool_mailbox",
            "label": "Claim pool mailbox",
            "description": "Claim a reusable mailbox, read registration mail, then complete or release the claim.",
            "steps": [
                {
                    "key": "claim_random",
                    "label": "Claim mailbox",
                    "description": "Claim a pool mailbox for one caller/task pair.",
                    "method": "POST",
                    "endpoint": endpoints["pool_claim_random"],
                    "auth": "api_key",
                    "request": {
                        "body_fields": pool_claim_body_fields,
                        "required_body_fields": ["caller_id", "task_id"],
                        "provider_selector": _integration_manifest_provider_selector(
                            pool_scope,
                            source="selection_policy.scopes.explicit_pool_claim",
                            default_field="provider",
                        ),
                    },
                    "response": {"field": "data", "email_field": "email", "claim_token_field": "claim_token"},
                    "next": {"success": "read_messages"},
                },
                _integration_manifest_action_step(
                    "read_messages",
                    pool_read_actions.get("read_messages") or {},
                    label="Read messages",
                    description="Read messages using the claimed mailbox email and claim token.",
                    response_field="emails",
                    next_action="read_verification_code",
                ),
                _integration_manifest_action_step(
                    "read_verification_code",
                    pool_read_actions.get("read_verification_code") or {},
                    label="Read verification code",
                    description="Extract a verification code using the claimed mailbox email and claim token.",
                    response_field="verification_code",
                    next_action="complete_claim",
                ),
                _integration_manifest_action_step(
                    "complete_claim",
                    pool_read_actions.get("complete_claim") or {},
                    label="Complete claim",
                    description="Mark the claim result after the registration task succeeds or fails.",
                    response_field="data",
                ),
                _integration_manifest_action_step(
                    "release_claim",
                    pool_read_actions.get("release_claim") or {},
                    label="Release claim",
                    description="Release the claim without recording a final registration result.",
                    response_field="data",
                ),
            ],
        },
        {
            "key": "create_task_temp_mailbox",
            "label": "Create task temp mailbox",
            "description": "Create a task-scoped temp mailbox, read registration mail, then finish the task mailbox lifecycle.",
            "steps": [
                {
                    "key": "apply_task_mailbox",
                    "label": "Create mailbox",
                    "description": "Create or reuse a task-scoped temp mailbox for one caller/task pair.",
                    "method": "POST",
                    "endpoint": endpoints["temp_mail_apply"],
                    "auth": "api_key",
                    "request": {
                        "body_fields": task_apply_body_fields,
                        "required_body_fields": ["caller_id", "task_id"],
                        "provider_selector": _integration_manifest_provider_selector(
                            task_scope,
                            source="selection_policy.scopes.task_temp_apply",
                            default_field="provider_name",
                        ),
                    },
                    "response": {"field": "data", "email_field": "email", "task_token_field": "task_token"},
                    "next": {"success": "read_messages"},
                },
                _integration_manifest_action_step(
                    "read_messages",
                    task_read_actions.get("read_messages") or {},
                    label="Read messages",
                    description="Read messages using the task mailbox email or claim token when provided.",
                    response_field="emails",
                    next_action="read_verification_code",
                ),
                _integration_manifest_action_step(
                    "read_verification_code",
                    task_read_actions.get("read_verification_code") or {},
                    label="Read verification code",
                    description="Extract a verification code from the task mailbox.",
                    response_field="verification_code",
                    next_action="finish_task_mailbox",
                ),
                _integration_manifest_action_step(
                    "finish_task_mailbox",
                    task_read_actions.get("finish_task_mailbox") or {},
                    label="Finish task mailbox",
                    description="Mark the task temp mailbox finished after the registration flow ends.",
                    response_field="data",
                ),
            ],
        },
    ]


def get_external_integration_manifest(
    *,
    deployment_profile: dict[str, Any] | None = None,
    selection_policy: dict[str, Any] | None = None,
    provider_filter: dict[str, Any] | None = None,
    provider_diagnostics: dict[str, Any] | None = None,
    provider_integration_guide: dict[str, Any] | None = None,
    endpoints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a secret-safe integration manifest for external projects."""
    if deployment_profile is None:
        deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
    if selection_policy is None:
        selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    if provider_filter is None:
        provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    if provider_diagnostics is None:
        provider_diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
    manifest_endpoints = _provider_integration_endpoint_map(endpoints)
    source_endpoints = endpoints if isinstance(endpoints, dict) else {}
    discovery_endpoints = {
        **manifest_endpoints,
        **{str(key): str(value) for key, value in source_endpoints.items() if str(key or "").strip() and value},
    }
    if provider_integration_guide is None:
        provider_integration_guide = get_provider_integration_guide(
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_filter=provider_filter,
            provider_diagnostics=provider_diagnostics,
            endpoints=manifest_endpoints,
        )
    selection_scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    guide_providers = (
        provider_integration_guide.get("providers") if isinstance(provider_integration_guide.get("providers"), list) else []
    )
    recipes = _provider_selection_recipe_bundle(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_integration_guide=provider_integration_guide,
    )
    quickstart = _integration_manifest_quickstart(
        endpoints=discovery_endpoints,
        selection_policy=selection_policy,
    )

    return {
        "version": 1,
        "documentation": get_provider_documentation_contract(),
        "auth": {
            "scheme": "api_key",
            "header": "X-API-Key",
            "placeholder": "<your-api-key>",
            "headers": {"X-API-Key": "<your-api-key>"},
            "curl_header": "X-API-Key: <your-api-key>",
        },
        "discovery": {
            "recommended_sequence": [
                {
                    "step": "capabilities",
                    "method": "GET",
                    "endpoint": manifest_endpoints["capabilities"],
                    "response_field": "integration_manifest",
                },
                {
                    "step": "providers",
                    "method": "GET",
                    "endpoint": manifest_endpoints["providers"],
                    "response_field": "integration_manifest",
                },
                {
                    "step": "mailboxes",
                    "method": "GET",
                    "endpoint": manifest_endpoints["mailboxes"],
                    "query": {"kind": "all", "provider": "all"},
                },
            ],
            "endpoints": discovery_endpoints,
        },
        "quickstart": quickstart,
        "selection": {
            "source_priority": list(selection_policy.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY),
            "active_allowlist": copy.deepcopy(selection_scopes.get("active_allowlist") or {}),
            "temp_runtime_default": copy.deepcopy(selection_scopes.get("temp_runtime_default") or {}),
            "pool_claim_default": copy.deepcopy(selection_scopes.get("pool_claim_default") or {}),
            "task_temp_apply": copy.deepcopy(selection_scopes.get("task_temp_apply") or {}),
            "explicit_pool_claim": copy.deepcopy(selection_scopes.get("explicit_pool_claim") or {}),
            "aliases": copy.deepcopy(provider_integration_guide.get("aliases") or deployment_profile.get("aliases") or {}),
            "recipes": copy.deepcopy(recipes.get("selection_recipes") or []),
            "recipe_index": copy.deepcopy(recipes.get("selection_recipe_index") or {}),
        },
        "deployment": {
            "env": copy.deepcopy(DEPLOYMENT_ENV_CONTRACT),
            "config_file": copy.deepcopy(selection_policy.get("config_file") or deployment_profile.get("config_file") or {}),
            "templates": copy.deepcopy(deployment_profile.get("templates") or {}),
            "source_priority": list(selection_policy.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY),
            "selection_recipes": copy.deepcopy(recipes.get("selection_recipes") or []),
            "selection_recipe_index": copy.deepcopy(recipes.get("selection_recipe_index") or {}),
        },
        "provider_filter": copy.deepcopy(provider_filter),
        "provider_diagnostics_summary": copy.deepcopy((provider_diagnostics or {}).get("summary") or {}),
        "secret_policy": copy.deepcopy(provider_integration_guide.get("secret_policy") or {}),
        "selection_recipes": copy.deepcopy(recipes.get("selection_recipes") or []),
        "selection_recipe_index": copy.deepcopy(recipes.get("selection_recipe_index") or {}),
        "workflows": _integration_manifest_workflows(
            endpoints=discovery_endpoints,
            selection_policy=selection_policy,
        ),
        "providers": [
            _integration_manifest_provider_entry(item)
            for item in guide_providers
            if isinstance(item, dict) and _normalize_provider_name(item.get("provider"))
        ],
    }


def get_mailbox_directory_provider_context(*, mailbox_inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return provider-selection context embedded in unified mailbox directories.

    The unified mailbox directory is often the first external payload a caller
    reads before choosing whether to claim from Outlook/IMAP inventory or create
    a temp mailbox. Keep this context machine-readable and secret-free so a
    caller can derive provider choices without making a second discovery request.
    """
    provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
    selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
    integration_guide = get_provider_integration_guide(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=diagnostics,
    )
    defaults = diagnostics.get("defaults") if isinstance(diagnostics.get("defaults"), dict) else {}
    temp_default = defaults.get("temp_mail_provider") if isinstance(defaults.get("temp_mail_provider"), dict) else {}
    pool_default = defaults.get("pool_claim_provider") if isinstance(defaults.get("pool_claim_provider"), dict) else {}
    discovery = {
        "providers_endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["providers"],
        "provider_health_endpoint": PROVIDER_HEALTH_ENDPOINT,
        "provider_health_fields": ["kind", "provider", "probe_network"],
        "provider_preflight_endpoint": PROVIDER_PREFLIGHT_ENDPOINT,
        "provider_preflight_fields": ["probe_network"],
    }
    readiness_summary = get_mailbox_provider_readiness_summary(
        mailbox_inventory=mailbox_inventory,
        provider_diagnostics=diagnostics,
        provider_integration_guide=integration_guide,
        selection_policy=selection_policy,
        discovery=discovery,
    )

    return {
        "version": 1,
        "defaults": {
            "temp_mail_provider": temp_default.get("provider") or "",
            "temp_mail_provider_env": TEMP_MAIL_PROVIDER_ENV,
            "pool_claim_provider": pool_default.get("provider") or "auto",
            "pool_claim_provider_env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
            "active_mailbox_providers": provider_filter.get("active_providers") or [],
            "active_mailbox_provider_env": ACTIVE_MAILBOX_PROVIDER_ENV,
        },
        "provider_filter": provider_filter,
        "provider_diagnostics": {
            "summary": diagnostics.get("summary") or {},
            "filter": diagnostics.get("filter") or {},
            "defaults": defaults,
            "scope": diagnostics.get("scope") or {},
        },
        "documentation": get_provider_documentation_contract(),
        "deployment_env": copy.deepcopy(DEPLOYMENT_ENV_CONTRACT),
        "deployment_profile": deployment_profile,
        "selection_policy": selection_policy,
        "provider_integration_guide": integration_guide,
        "readiness_summary": readiness_summary,
        "discovery": discovery,
    }
