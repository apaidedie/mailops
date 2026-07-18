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
from .constants import (
    _BRIDGE_OPERATOR_CANONICAL,
    _BRIDGE_OPERATOR_FAMILY,
    _TEMP_PROVIDER_LABEL_OVERRIDES,
    _TEMP_PROVIDER_ZH_LABEL_OVERRIDES,
    ACTIVE_MAILBOX_PROVIDER_ENV,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    GPTMAIL_POOL_TEMP_PROVIDER_NAMES,
    GPTMAIL_RUNTIME_ALIASES,
    LEGACY_ACCOUNT_POOL_ALIASES,
    PROVIDER_SELECTION_SOURCE_PRIORITY,
    TEMP_MAIL_PROVIDER_ENV,
)
from .endpoints import (
    _CANONICAL_EXTERNAL_ENDPOINTS,
    _LEGACY_EXTERNAL_ENDPOINTS,
    EXTERNAL_API_LEGACY_PREFIX,
    EXTERNAL_API_V1_PREFIX,
    EXTERNAL_READ_ENDPOINTS,
    EXTERNAL_READ_QUERY_FIELDS,
    LEGACY_PROVIDER_HEALTH_ENDPOINT,
    LEGACY_PROVIDER_PREFLIGHT_ENDPOINT,
    MAILBOX_SESSION_CLOSE_ENDPOINT,
    MAILBOX_SESSION_READ_ENDPOINT,
    MAILBOX_SESSION_START_ENDPOINT,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    _action_contract_next_actions_for_endpoint_map,
    _external_api_endpoint_map,
    _external_api_path,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_api_legacy_endpoint_map,
    get_external_mailbox_read_contract,
    get_provider_documentation_contract,
)

_TEMP_PROVIDER_CONFIG_CONTRACTS = {
    "custom_domain_temp_mail": {
        "settings_keys": [
            "temp_mail_api_base_url",
            "temp_mail_api_key",
            "temp_mail_domains",
            "temp_mail_default_domain",
            "temp_mail_prefix_rules",
        ],
        "required_settings": ["temp_mail_api_key"],
        "required_env": ["GPTMAIL_API_KEY"],
        "optional_env": ["GPTMAIL_BASE_URL"],
        "settings_defaults": {
            "temp_mail_api_base_url": "https://mail.chatgpt.org.uk",
            "temp_mail_domains": [],
            "temp_mail_prefix_rules": {
                "min_length": 1,
                "max_length": 32,
                "pattern": "^[a-z0-9][a-z0-9._-]*$",
            },
        },
        "env_defaults": {"GPTMAIL_BASE_URL": "https://mail.chatgpt.org.uk"},
        "secret_settings": ["temp_mail_api_key"],
        "secret_env": ["GPTMAIL_API_KEY"],
        "config_schema": {
            "fields": [
                {
                    "key": "temp_mail_api_base_url",
                    "label": "GPTMail API Base URL",
                    "type": "url",
                    "placeholder": "https://mail.chatgpt.org.uk",
                    "default": "https://mail.chatgpt.org.uk",
                },
                {
                    "key": "temp_mail_api_key",
                    "label": "GPTMail API Key",
                    "type": "password",
                    "required": True,
                },
                {
                    "key": "temp_mail_domains",
                    "label": "Available domains (JSON)",
                    "type": "json",
                    "default": [],
                    "placeholder": '[{"name": "mail.example.com", "enabled": true}]',
                },
                {
                    "key": "temp_mail_default_domain",
                    "label": "Default domain",
                    "type": "text",
                    "placeholder": "mail.example.com",
                },
                {
                    "key": "temp_mail_prefix_rules",
                    "label": "Prefix rules (JSON)",
                    "type": "json",
                    "default": {
                        "min_length": 1,
                        "max_length": 32,
                        "pattern": "^[a-z0-9][a-z0-9._-]*$",
                    },
                },
            ]
        },
    },
    "legacy_bridge": {
        "settings_keys": [
            "temp_mail_api_base_url",
            "temp_mail_api_key",
            "temp_mail_domains",
            "temp_mail_default_domain",
            "temp_mail_prefix_rules",
        ],
        "required_settings": ["temp_mail_api_key"],
        "required_env": ["GPTMAIL_API_KEY"],
        "optional_env": ["GPTMAIL_BASE_URL"],
        "settings_defaults": {
            "temp_mail_api_base_url": "https://mail.chatgpt.org.uk",
            "temp_mail_domains": [],
            "temp_mail_prefix_rules": {
                "min_length": 1,
                "max_length": 32,
                "pattern": "^[a-z0-9][a-z0-9._-]*$",
            },
        },
        "env_defaults": {"GPTMAIL_BASE_URL": "https://mail.chatgpt.org.uk"},
        "secret_settings": ["temp_mail_api_key"],
        "secret_env": ["GPTMAIL_API_KEY"],
        "config_schema": {
            "fields": [
                {
                    "key": "temp_mail_api_base_url",
                    "label": "GPTMail API Base URL",
                    "type": "url",
                    "placeholder": "https://mail.chatgpt.org.uk",
                    "default": "https://mail.chatgpt.org.uk",
                },
                {
                    "key": "temp_mail_api_key",
                    "label": "GPTMail API Key",
                    "type": "password",
                    "required": True,
                },
                {
                    "key": "temp_mail_domains",
                    "label": "Available domains (JSON)",
                    "type": "json",
                    "default": [],
                    "placeholder": '[{"name": "mail.example.com", "enabled": true}]',
                },
                {
                    "key": "temp_mail_default_domain",
                    "label": "Default domain",
                    "type": "text",
                    "placeholder": "mail.example.com",
                },
                {
                    "key": "temp_mail_prefix_rules",
                    "label": "Prefix rules (JSON)",
                    "type": "json",
                    "default": {
                        "min_length": 1,
                        "max_length": 32,
                        "pattern": "^[a-z0-9][a-z0-9._-]*$",
                    },
                },
            ]
        },
    },
    "cloudflare_temp_mail": {
        "settings_keys": [
            "cf_worker_base_url",
            "cf_worker_admin_key",
            "cf_worker_domains",
            "cf_worker_default_domain",
            "cf_worker_prefix_rules",
        ],
        "required_settings": ["cf_worker_base_url", "cf_worker_admin_key"],
        "required_env": ["CF_WORKER_BASE_URL", "CF_WORKER_ADMIN_KEY"],
        "optional_env": [],
        "settings_defaults": {
            "cf_worker_domains": [],
            "cf_worker_prefix_rules": {
                "min_length": 1,
                "max_length": 32,
                "pattern": "^[a-z0-9][a-z0-9._-]*$",
            },
        },
        "env_defaults": {},
        "secret_settings": ["cf_worker_admin_key"],
        "secret_env": ["CF_WORKER_ADMIN_KEY"],
        "config_schema": {
            "fields": [
                {
                    "key": "cf_worker_base_url",
                    "label": "CF Worker base URL",
                    "type": "url",
                    "required": True,
                    "placeholder": "https://mail.yourname.workers.dev",
                },
                {
                    "key": "cf_worker_admin_key",
                    "label": "CF Worker Admin password",
                    "type": "password",
                    "required": True,
                },
                {
                    "key": "cf_worker_domains",
                    "label": "Available domains (readonly)",
                    "type": "json",
                    "readonly": True,
                    "default": [],
                },
                {
                    "key": "cf_worker_default_domain",
                    "label": "Default domain (readonly)",
                    "type": "text",
                    "readonly": True,
                },
                {
                    "key": "cf_worker_prefix_rules",
                    "label": "Prefix rules (JSON)",
                    "type": "json",
                    "default": {
                        "min_length": 1,
                        "max_length": 32,
                        "pattern": "^[a-z0-9][a-z0-9._-]*$",
                    },
                },
            ]
        },
    },
    "mail_tm": {
        "settings_keys": [],
        "required_settings": [],
        "required_env": [],
        "optional_env": ["MAILTM_API_BASE"],
        "settings_defaults": {},
        "env_defaults": {"MAILTM_API_BASE": settings_repo.MAILTM_DEFAULT_API_BASE},
        "secret_settings": [],
        "secret_env": [],
    },
    "duckmail": {
        "settings_keys": ["duckmail_api_base", "duckmail_bearer_token"],
        "required_settings": ["duckmail_bearer_token"],
        "required_env": ["DUCKMAIL_BEARER_TOKEN"],
        "optional_env": ["DUCKMAIL_API_BASE"],
        "settings_defaults": {"duckmail_api_base": settings_repo.DUCKMAIL_DEFAULT_API_BASE},
        "env_defaults": {"DUCKMAIL_API_BASE": settings_repo.DUCKMAIL_DEFAULT_API_BASE},
        "secret_settings": ["duckmail_bearer_token"],
        "secret_env": ["DUCKMAIL_BEARER_TOKEN"],
        "config_schema": {
            "fields": [
                {
                    "key": "duckmail_api_base",
                    "label": "DuckMail API Base URL",
                    "type": "url",
                    "placeholder": settings_repo.DUCKMAIL_DEFAULT_API_BASE,
                    "default": settings_repo.DUCKMAIL_DEFAULT_API_BASE,
                },
                {
                    "key": "duckmail_bearer_token",
                    "label": "DuckMail Bearer Token",
                    "type": "password",
                    "required": True,
                },
            ]
        },
    },
    "tempmail_lol": {
        "settings_keys": ["tempmail_lol_api_key", "temp_mail_lol_api_key"],
        "required_settings": [],
        "required_env": [],
        "optional_env": ["TEMPMAIL_LOL_API_KEY", "TEMP_MAIL_LOL_API_KEY"],
        "settings_defaults": {},
        "env_defaults": {},
        "secret_settings": ["tempmail_lol_api_key", "temp_mail_lol_api_key"],
        "secret_env": ["TEMPMAIL_LOL_API_KEY", "TEMP_MAIL_LOL_API_KEY"],
        "config_schema": {
            "fields": [
                {
                    "key": "tempmail_lol_api_key",
                    "label": "TempMail.lol API Key",
                    "type": "password",
                    "required": False,
                }
            ]
        },
    },
    "emailnator": {
        "settings_keys": ["emailnator_api_key", "emailnator_email_types"],
        "required_settings": ["emailnator_api_key"],
        "required_env": ["EMAILNATOR_API_KEY"],
        "optional_env": ["EMAILNATOR_EMAIL_TYPES"],
        "settings_defaults": {"emailnator_email_types": list(settings_repo.EMAILNATOR_DEFAULT_EMAIL_TYPES)},
        "env_defaults": {"EMAILNATOR_EMAIL_TYPES": '["public_gmail_plus"]'},
        "secret_settings": ["emailnator_api_key"],
        "secret_env": ["EMAILNATOR_API_KEY"],
        "config_schema": {
            "fields": [
                {
                    "key": "emailnator_api_key",
                    "label": "Emailnator RapidAPI Key",
                    "type": "password",
                    "required": True,
                },
                {
                    "key": "emailnator_email_types",
                    "label": "Email types",
                    "type": "json",
                    "default": list(settings_repo.EMAILNATOR_DEFAULT_EMAIL_TYPES),
                    "placeholder": '["public_gmail_plus"]',
                },
            ]
        },
    },
}

_TEMP_PROVIDER_SETTINGS_UI = {
    "legacy_bridge": {
        "panel": "schema",
        "description": "GPTMail temporary-mail API (mail.chatgpt.org.uk compatible)",
        "description_zh": "GPTMail 临时邮箱 API（兼容 mail.chatgpt.org.uk）",
        "sort_order": 10,
        "actions": [
            {
                "key": "check_usage",
                "label": "Refresh usage",
                "label_zh": "刷新用量",
                "method": "GET",
                "endpoint": "/api/providers/temp/legacy_bridge/health?probe_network=true",
            }
        ],
    },
    # Historical catalog key kept for inventory/source compatibility; settings UI
    # treats it as the same schema panel as legacy_bridge / GPTMail.
    "custom_domain_temp_mail": {
        "panel": "schema",
        "description": "GPTMail temporary-mail API (mail.chatgpt.org.uk compatible)",
        "description_zh": "GPTMail 临时邮箱 API（兼容 mail.chatgpt.org.uk）",
        "sort_order": 10,
        "actions": [
            {
                "key": "check_usage",
                "label": "Refresh usage",
                "label_zh": "刷新用量",
                "method": "GET",
                "endpoint": "/api/providers/temp/legacy_bridge/health?probe_network=true",
            }
        ],
    },
    "cloudflare_temp_mail": {
        "panel": "schema",
        "description": "Cloudflare Worker temporary-mail deployment",
        "description_zh": "Cloudflare Worker 部署的临时邮箱",
        "sort_order": 20,
        "actions": [
            {
                "key": "sync_domains",
                "label": "Sync domains from CF Worker",
                "label_zh": "从 CF Worker 同步域名",
                "method": "POST",
                "endpoint": "/api/settings/cf-worker-sync-domains",
                "result_map": {
                    "domains": "cf_worker_domains",
                    "default_domain": "cf_worker_default_domain",
                },
            }
        ],
    },
    "mail_tm": {
        "description": "Public Mail.tm temporary-mail service",
        "description_zh": "公开 Mail.tm 临时邮箱服务",
        "sort_order": 30,
    },
    "duckmail": {
        "description": "Mail.tm-compatible DuckMail service",
        "description_zh": "兼容 Mail.tm 协议的 DuckMail 服务",
        "sort_order": 40,
    },
    "tempmail_lol": {
        "description": "Public TempMail.lol temporary-mail service",
        "description_zh": "公开 TempMail.lol 临时邮箱服务",
        "sort_order": 50,
    },
    "emailnator": {
        "description": "Emailnator temporary Gmail service",
        "description_zh": "Emailnator 临时 Gmail 服务",
        "sort_order": 60,
    },
}

_PROVIDER_CAPABILITY_READ_ACTIONS = [
    "messages",
    "latest_message",
    "message_detail",
    "message_raw",
    "verification_code",
    "verification_link",
    "wait_message",
]

_PROVIDER_CAPABILITY_WORKFLOWS = {
    "mailbox_session": "Provider-neutral mailbox session",
    "pool_claim": "Mailbox pool claim",
    "task_temp_mailbox": "Task temp-mailbox",
    "mailbox_directory": "Unified mailbox directory",
    "provider_health": "Provider health check",
}

_SECRET_FIELD_HINTS = ("key", "token", "secret", "password", "bearer")


def _plugin_settings_key(provider_name: str, field_key: str) -> str:
    return f"plugin.{provider_name}.{field_key}"


def _plugin_field_is_secret(field: dict[str, Any]) -> bool:
    field_type = str(field.get("type") or "").strip().lower()
    field_key = str(field.get("key") or "").strip().lower()
    return field_type == "password" or any(hint in field_key for hint in _SECRET_FIELD_HINTS)


def _plugin_config_schema(provider_info: dict[str, Any]) -> dict[str, Any]:
    schema = provider_info.get("config_schema")
    if not isinstance(schema, dict):
        return {}
    sanitized = copy.deepcopy(schema)
    fields = sanitized.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict) and _plugin_field_is_secret(field):
                field.pop("default", None)
    return sanitized


def _plugin_provider_configuration_contract(provider_name: str, provider_info: dict[str, Any]) -> dict[str, Any]:
    schema = _plugin_config_schema(provider_info)
    fields = schema.get("fields") if isinstance(schema, dict) else []
    settings_keys: list[str] = []
    required_settings: list[str] = []
    secret_settings: list[str] = []
    settings_defaults: dict[str, Any] = {}

    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_key = str(field.get("key") or "").strip()
            if not field_key:
                continue
            setting_key = _plugin_settings_key(provider_name, field_key)
            is_secret = _plugin_field_is_secret(field)
            settings_keys.append(setting_key)
            if bool(field.get("required")):
                required_settings.append(setting_key)
            if "default" in field and not is_secret:
                settings_defaults[setting_key] = copy.deepcopy(field.get("default"))
            if is_secret:
                secret_settings.append(setting_key)

    return {
        "settings_keys": settings_keys,
        "required_settings": required_settings,
        "required_env": [],
        "optional_env": [],
        "settings_defaults": settings_defaults,
        "env_defaults": {},
        "secret_settings": secret_settings,
        "secret_env": [],
        "config_schema": schema,
    }


def _temp_provider_configuration_contract(provider_name: str, provider_info: dict[str, Any] | None = None) -> dict[str, Any]:
    if provider_name not in _TEMP_PROVIDER_CONFIG_CONTRACTS and provider_info is not None:
        return _plugin_provider_configuration_contract(provider_name, provider_info)

    contract = dict(_TEMP_PROVIDER_CONFIG_CONTRACTS.get(provider_name, {}))
    return {
        "settings_keys": list(contract.get("settings_keys") or []),
        "required_settings": list(contract.get("required_settings") or []),
        "required_env": list(contract.get("required_env") or []),
        "optional_env": list(contract.get("optional_env") or []),
        "settings_defaults": copy.deepcopy(contract.get("settings_defaults") or {}),
        "env_defaults": copy.deepcopy(contract.get("env_defaults") or {}),
        "secret_settings": list(contract.get("secret_settings") or []),
        "secret_env": list(contract.get("secret_env") or []),
        "config_schema": copy.deepcopy(contract.get("config_schema") or {}),
    }


def _temp_provider_selection_contract(provider_name: str) -> dict[str, Any]:
    return {
        "runtime_env": {TEMP_MAIL_PROVIDER_ENV: provider_name},
        "pool_claim_provider": provider_name,
        "temp_apply_provider_name": provider_name,
        "pool_claim_temp_provider_names": [provider_name],
        "accepted_aliases": list(GPTMAIL_RUNTIME_ALIASES) if provider_name == "legacy_bridge" else [],
    }


def _temp_provider_settings_ui_contract(
    provider_name: str,
    configuration: dict[str, Any],
    provider_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = copy.deepcopy(_TEMP_PROVIDER_SETTINGS_UI.get(provider_name) or {})
    # Keep settings-page alias coverage for legacy bridge historical names.
    # Runtime selection still uses GPTMAIL_RUNTIME_ALIASES; settings_ui aliases
    # additionally include custom_domain_temp_mail for saved-value normalization.
    if provider_name == "legacy_bridge":
        aliases = list(dict.fromkeys([*GPTMAIL_RUNTIME_ALIASES, "custom_domain_temp_mail"]))
    else:
        aliases = []
    schema = configuration.get("config_schema") if isinstance(configuration.get("config_schema"), dict) else {}
    fields = schema.get("fields") if isinstance(schema.get("fields"), list) else []
    actions = metadata.get("actions") if isinstance(metadata.get("actions"), list) else []
    is_plugin = provider_name not in _TEMP_PROVIDER_CONFIG_CONTRACTS and provider_info is not None
    return {
        "panel": str(metadata.get("panel") or "schema"),
        "description": str(
            metadata.get("description") or ("Third-party provider plugin" if is_plugin else "Temporary-mail provider")
        ),
        "description_zh": str(metadata.get("description_zh") or ("第三方临时邮箱插件" if is_plugin else "临时邮箱 Provider")),
        "sort_order": int(metadata.get("sort_order") or (1000 if is_plugin else 500)),
        "aliases": aliases,
        "fields": copy.deepcopy(fields),
        "actions": copy.deepcopy(actions),
    }


def _account_provider_configuration_contract(provider_name: str, account_type: str) -> dict[str, Any]:
    base_contract: dict[str, Any] = {"required_env": [], "optional_env": []}
    if provider_name == "auto":
        return {**base_contract, "account_import_fields": ["auto_detect_line"], "secret_fields": []}
    if account_type == "outlook":
        return {
            **base_contract,
            "account_import_fields": ["email", "client_id", "refresh_token"],
            "secret_fields": ["refresh_token"],
        }
    if provider_name == "custom":
        return {
            **base_contract,
            "account_import_fields": ["email", "password", "imap_host", "imap_port"],
            "secret_fields": ["password"],
        }
    return {**base_contract, "account_import_fields": ["email", "password"], "secret_fields": ["password"]}


def _plugin_provider_config_status(provider_name: str, provider_info: dict[str, Any]) -> dict[str, Any]:
    configuration = _plugin_provider_configuration_contract(provider_name, provider_info)
    missing: list[str] = []
    for setting_key in configuration["required_settings"]:
        value = settings_repo.get_setting(setting_key, "").strip()
        if not value:
            missing.append(setting_key)
    return {"configured": not missing, "missing_config": missing}


def _account_provider_selection_contract(provider_name: str) -> dict[str, Any]:
    return {
        "pool_claim_provider": provider_name,
        "temp_apply_provider_name": None,
        "runtime_env": {},
        "pool_claim_temp_fallback_provider_names": list(GPTMAIL_POOL_TEMP_PROVIDER_NAMES) if provider_name == "custom" else [],
        "accepted_aliases": [],
    }


def get_provider_alias_contract() -> dict[str, Any]:
    return {
        "runtime_temp_mail_provider_aliases": {
            alias: settings_repo.LEGACY_TEMP_MAIL_PROVIDER for alias in GPTMAIL_RUNTIME_ALIASES
        },
        "pool_claim_provider_aliases": {
            "imap": {
                "kind": "account",
                "pool_claim_provider": "imap",
                "canonical_provider": None,
                "temp_provider_names": [],
            },
            **{
                alias: {
                    "kind": "temp_family",
                    "pool_claim_provider": alias,
                    "canonical_provider": settings_repo.LEGACY_TEMP_MAIL_PROVIDER,
                    "temp_provider_names": list(GPTMAIL_POOL_TEMP_PROVIDER_NAMES),
                    "temp_apply_provider_name": settings_repo.LEGACY_TEMP_MAIL_PROVIDER,
                    "runtime_env": {TEMP_MAIL_PROVIDER_ENV: settings_repo.LEGACY_TEMP_MAIL_PROVIDER},
                }
                for alias in GPTMAIL_RUNTIME_ALIASES
            },
        },
    }


def _provider_deployment_contract(item: dict[str, Any]) -> dict[str, Any]:
    provider_name = str(item.get("provider") or "").strip()
    selection = item.get("selection") if isinstance(item.get("selection"), dict) else {}
    configuration = item.get("configuration") if isinstance(item.get("configuration"), dict) else {}
    pool_claim_provider = str(selection.get("pool_claim_provider") or provider_name).strip()
    temp_apply_provider = str(selection.get("temp_apply_provider_name") or "").strip()
    runtime_env = selection.get("runtime_env") if isinstance(selection.get("runtime_env"), dict) else {}
    runtime_provider = str(runtime_env.get(TEMP_MAIL_PROVIDER_ENV) or "").strip()

    contract: dict[str, Any] = {
        "activate": {
            "env": ACTIVE_MAILBOX_PROVIDER_ENV,
            "value": provider_name,
            "settings_key": "active_mailbox_providers",
            "settings_value": provider_name,
        },
        "pool_claim_default": {
            "env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
            "value": pool_claim_provider,
            "settings_key": "pool_default_provider",
            "settings_value": pool_claim_provider,
        },
        "pool_claim_request": {"field": "provider", "value": pool_claim_provider},
        "config_env": {
            "required": list(configuration.get("required_env") or []),
            "optional": list(configuration.get("optional_env") or []),
            "defaults": copy.deepcopy(configuration.get("env_defaults") or {}),
            "secret": list(configuration.get("secret_env") or []),
        },
        "config_settings": {
            "keys": list(configuration.get("settings_keys") or []),
            "required": list(configuration.get("required_settings") or []),
            "defaults": copy.deepcopy(configuration.get("settings_defaults") or {}),
            "secret": list(configuration.get("secret_settings") or []),
        },
    }
    if runtime_provider:
        contract["runtime_default"] = {
            "env": TEMP_MAIL_PROVIDER_ENV,
            "value": runtime_provider,
            "settings_key": "temp_mail_provider",
            "settings_value": runtime_provider,
        }
    if temp_apply_provider:
        contract["task_temp_apply_request"] = {"field": "provider_name", "value": temp_apply_provider}
    return contract


def _append_unique(target: list[str], values: Any) -> None:
    if values in (None, ""):
        return
    source_values = values if isinstance(values, (list, tuple, set)) else [values]
    seen = set(target)
    for value in source_values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        target.append(text)
        seen.add(text)


def _provider_recipe_key(scope: str, provider: str) -> str:
    return f"{scope}:{provider}"


def _provider_recipe_alias_canonical(provider: str, aliases: dict[str, Any]) -> str:
    runtime_aliases = (
        aliases.get("runtime_temp_mail_provider_aliases")
        if isinstance(aliases.get("runtime_temp_mail_provider_aliases"), dict)
        else {}
    )
    if provider in runtime_aliases:
        return _normalize_provider_name(runtime_aliases.get(provider))
    pool_aliases = (
        aliases.get("pool_claim_provider_aliases") if isinstance(aliases.get("pool_claim_provider_aliases"), dict) else {}
    )
    alias_info = pool_aliases.get(provider) if isinstance(pool_aliases.get(provider), dict) else {}
    return _normalize_provider_name(alias_info.get("canonical_provider"))


def _provider_recipe_label(provider: str, provider_examples: dict[str, dict[str, Any]], aliases: dict[str, Any]) -> str:
    example = provider_examples.get(provider) if isinstance(provider_examples.get(provider), dict) else {}
    if example.get("label"):
        return str(example.get("label") or provider)
    canonical = _provider_recipe_alias_canonical(provider, aliases)
    canonical_example = (
        provider_examples.get(canonical) if canonical and isinstance(provider_examples.get(canonical), dict) else {}
    )
    if canonical_example.get("label"):
        return str(canonical_example.get("label"))
    return provider


def _provider_recipe_kind(provider: str, provider_examples: dict[str, dict[str, Any]], aliases: dict[str, Any]) -> str:
    example = provider_examples.get(provider) if isinstance(provider_examples.get(provider), dict) else {}
    kind = str(example.get("kind") or "").strip().lower()
    if kind:
        return kind
    pool_aliases = (
        aliases.get("pool_claim_provider_aliases") if isinstance(aliases.get("pool_claim_provider_aliases"), dict) else {}
    )
    alias_info = pool_aliases.get(provider) if isinstance(pool_aliases.get(provider), dict) else {}
    alias_kind = str(alias_info.get("kind") or "").strip().lower()
    if alias_kind == "account":
        return "account"
    if alias_kind:
        return "temp"
    return "temp" if _provider_recipe_alias_canonical(provider, aliases) else "unknown"


def _provider_recipe_active(provider: str, provider_examples: dict[str, dict[str, Any]], aliases: dict[str, Any]) -> bool:
    example = provider_examples.get(provider) if isinstance(provider_examples.get(provider), dict) else {}
    if "active" in example:
        return bool(example.get("active"))
    canonical = _provider_recipe_alias_canonical(provider, aliases)
    canonical_example = (
        provider_examples.get(canonical) if canonical and isinstance(provider_examples.get(canonical), dict) else {}
    )
    if "active" in canonical_example:
        return bool(canonical_example.get("active"))
    return True


def _provider_recipe_env_hints(provider_entry: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(provider_entry, dict):
        return []
    configuration = provider_entry.get("configuration") if isinstance(provider_entry.get("configuration"), dict) else {}
    required_env = list(provider_entry.get("required_env") or configuration.get("required_env") or [])
    optional_env = list(provider_entry.get("optional_env") or configuration.get("optional_env") or [])
    env_keys: list[str] = []
    _append_unique(env_keys, required_env)
    _append_unique(env_keys, optional_env)
    from .integration import _integration_manifest_key_hints

    return _integration_manifest_key_hints(
        env_keys,
        required_keys=required_env,
        secret_keys=provider_entry.get("secret_env") or configuration.get("secret_env") or [],
        defaults=configuration.get("env_defaults") or {},
    )


def _provider_recipe_config_patch(key: str, value: Any) -> dict[str, Any]:
    return {"providers": {key: copy.deepcopy(value)}}


def _provider_recipe_config_examples(key: str, value: Any) -> dict[str, Any]:
    patch = _provider_recipe_config_patch(key, value)
    if isinstance(value, list):
        toml_value = "[" + ", ".join(json.dumps(str(item), ensure_ascii=False) for item in value) + "]"
    else:
        toml_value = json.dumps(value, ensure_ascii=False)
    return {
        "object": patch,
        "json": json.dumps(patch, ensure_ascii=False, indent=2) + "\n",
        "toml": "[providers]\n" + f"{key} = {toml_value}\n",
    }


def _provider_recipe_common(
    *,
    scope: str,
    provider: str,
    deployment_profile: dict[str, Any],
    selection_policy: dict[str, Any],
    provider_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    aliases = deployment_profile.get("aliases") if isinstance(deployment_profile.get("aliases"), dict) else {}
    provider_examples = (
        deployment_profile.get("provider_examples") if isinstance(deployment_profile.get("provider_examples"), dict) else {}
    )
    example = provider_examples.get(provider) if isinstance(provider_examples.get(provider), dict) else {}
    canonical = _provider_recipe_alias_canonical(provider, aliases)
    canonical_example = (
        provider_examples.get(canonical) if canonical and isinstance(provider_examples.get(canonical), dict) else {}
    )
    hint_source = provider_entry if isinstance(provider_entry, dict) else (example or canonical_example)
    return {
        "key": _provider_recipe_key(scope, provider),
        "scope": scope,
        "provider": provider,
        "label": _provider_recipe_label(provider, provider_examples, aliases),
        "kind": _provider_recipe_kind(provider, provider_examples, aliases),
        "active": _provider_recipe_active(provider, provider_examples, aliases),
        "source_priority": list(selection_policy.get("source_priority") or PROVIDER_SELECTION_SOURCE_PRIORITY),
        "provider_env": _provider_recipe_env_hints(hint_source),
    }


def _provider_selection_recipe_bundle(
    *,
    deployment_profile: dict[str, Any],
    selection_policy: dict[str, Any],
    provider_integration_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_values = (
        deployment_profile.get("provider_values") if isinstance(deployment_profile.get("provider_values"), dict) else {}
    )
    selection_scopes = selection_policy.get("scopes") if isinstance(selection_policy.get("scopes"), dict) else {}
    guide_providers = (
        provider_integration_guide.get("providers")
        if isinstance(provider_integration_guide, dict) and isinstance(provider_integration_guide.get("providers"), list)
        else []
    )
    provider_entries = {
        _normalize_provider_name(item.get("provider")): item
        for item in guide_providers
        if isinstance(item, dict) and _normalize_provider_name(item.get("provider"))
    }
    recipes: list[dict[str, Any]] = []
    aliases = deployment_profile.get("aliases") if isinstance(deployment_profile.get("aliases"), dict) else {}

    def provider_entry_for(provider: str) -> dict[str, Any] | None:
        return provider_entries.get(provider) or provider_entries.get(_provider_recipe_alias_canonical(provider, aliases))

    def add_recipe(recipe: dict[str, Any]) -> None:
        if not recipe.get("provider") or any(item.get("key") == recipe.get("key") for item in recipes):
            return
        recipes.append(recipe)

    active_scope = (
        selection_scopes.get("active_allowlist") if isinstance(selection_scopes.get("active_allowlist"), dict) else {}
    )
    active_values = active_scope.get("allowed_values") or provider_values.get("active_allowlist") or []
    for provider in [value for value in active_values if _normalize_provider_name(value) != "auto"]:
        normalized = _normalize_provider_name(provider)
        if not normalized:
            continue
        entry = provider_entry_for(normalized)
        recipe = _provider_recipe_common(
            scope="active_allowlist",
            provider=normalized,
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_entry=entry,
        )
        recipe.update(
            {
                "description": "Activate this mailbox source in provider discovery, pool claims, and task temp-mail creation.",
                "configuration": {
                    "env": {ACTIVE_MAILBOX_PROVIDER_ENV: normalized},
                    "provider_config": _provider_recipe_config_examples("active_mailbox_providers", [normalized]),
                    "settings": {str(active_scope.get("settings_key") or "active_mailbox_providers"): [normalized]},
                },
            }
        )
        add_recipe(recipe)

    temp_scope = (
        selection_scopes.get("temp_runtime_default") if isinstance(selection_scopes.get("temp_runtime_default"), dict) else {}
    )
    for provider in temp_scope.get("allowed_values") or provider_values.get("temp_runtime") or []:
        normalized = _normalize_provider_name(provider)
        if not normalized:
            continue
        entry = provider_entry_for(normalized)
        recipe = _provider_recipe_common(
            scope="temp_runtime_default",
            provider=normalized,
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_entry=entry,
        )
        recipe.update(
            {
                "description": "Use this temp-mail provider when app-side temp-mail creation does not pass an explicit provider.",
                "request": {"field": str(temp_scope.get("request_field") or "provider_name"), "value": normalized},
                "configuration": {
                    "env": {TEMP_MAIL_PROVIDER_ENV: normalized},
                    "provider_config": _provider_recipe_config_examples("temp_mail_provider", normalized),
                    "settings": {str(temp_scope.get("settings_key") or "temp_mail_provider"): normalized},
                },
            }
        )
        add_recipe(recipe)

    pool_default_scope = (
        selection_scopes.get("pool_claim_default") if isinstance(selection_scopes.get("pool_claim_default"), dict) else {}
    )
    pool_values = [
        value
        for value in (pool_default_scope.get("allowed_values") or provider_values.get("pool_claim") or [])
        if _normalize_provider_name(value) != "auto"
    ]
    for provider in pool_values:
        normalized = _normalize_provider_name(provider)
        if not normalized:
            continue
        entry = provider_entry_for(normalized)
        recipe = _provider_recipe_common(
            scope="pool_claim_default",
            provider=normalized,
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_entry=entry,
        )
        recipe.update(
            {
                "description": "Use this mailbox source when external pool claim-random omits a provider.",
                "request": {"field": str(pool_default_scope.get("request_field") or "provider"), "value": normalized},
                "configuration": {
                    "env": {EXTERNAL_POOL_DEFAULT_PROVIDER_ENV: normalized},
                    "provider_config": _provider_recipe_config_examples("pool_default_provider", normalized),
                    "settings": {str(pool_default_scope.get("settings_key") or "pool_default_provider"): normalized},
                },
            }
        )
        add_recipe(recipe)

    explicit_pool_scope = (
        selection_scopes.get("explicit_pool_claim") if isinstance(selection_scopes.get("explicit_pool_claim"), dict) else {}
    )
    for provider in [
        value
        for value in (explicit_pool_scope.get("allowed_values") or provider_values.get("pool_claim") or [])
        if _normalize_provider_name(value) != "auto"
    ]:
        normalized = _normalize_provider_name(provider)
        if not normalized:
            continue
        entry = provider_entry_for(normalized)
        request_field = str(explicit_pool_scope.get("request_field") or "provider")
        recipe = _provider_recipe_common(
            scope="explicit_pool_claim",
            provider=normalized,
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_entry=entry,
        )
        recipe.update(
            {
                "description": "Claim one mailbox from this source for a single external request.",
                "endpoint": str(explicit_pool_scope.get("endpoint") or _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_random"]),
                "request": {
                    "method": "POST",
                    "field": request_field,
                    "value": normalized,
                    "body": {request_field: normalized},
                    "required_body_fields": ["caller_id", "task_id"],
                },
            }
        )
        add_recipe(recipe)

    task_scope = selection_scopes.get("task_temp_apply") if isinstance(selection_scopes.get("task_temp_apply"), dict) else {}
    for provider in task_scope.get("allowed_values") or provider_values.get("temp_apply") or []:
        normalized = _normalize_provider_name(provider)
        if not normalized:
            continue
        entry = provider_entry_for(normalized)
        request_field = str(task_scope.get("request_field") or "provider_name")
        recipe = _provider_recipe_common(
            scope="task_temp_apply",
            provider=normalized,
            deployment_profile=deployment_profile,
            selection_policy=selection_policy,
            provider_entry=entry,
        )
        recipe.update(
            {
                "description": "Create a task-scoped temp mailbox from this provider for one external automation task.",
                "endpoint": str(task_scope.get("endpoint") or _CANONICAL_EXTERNAL_ENDPOINTS["temp_mail_apply"]),
                "request": {
                    "method": "POST",
                    "field": request_field,
                    "value": normalized,
                    "body": {request_field: normalized},
                    "required_body_fields": ["caller_id", "task_id"],
                },
            }
        )
        add_recipe(recipe)

    return {
        "selection_recipes": recipes,
        "selection_recipe_index": {str(item.get("key")): copy.deepcopy(item) for item in recipes if item.get("key")},
    }


def _merge_defaults(target: dict[str, Any], values: Any) -> None:
    if not isinstance(values, dict):
        return
    for key, value in values.items():
        text_key = str(key or "").strip()
        if not text_key or text_key in target:
            continue
        target[text_key] = copy.deepcopy(value)


def _template_env_value(key: str, defaults: dict[str, Any], secret_keys: set[str]) -> str:
    if key in secret_keys:
        return ""
    value = defaults.get(key, "")
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    if not text:
        return ""
    if text != text.strip() or "#" in text or any(char in text for char in "\r\n\t "):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
        return f'"{escaped}"'
    return text


def _deployment_profile_templates(
    *,
    env_defaults: dict[str, Any],
    env_secret: list[str],
    env_required: list[str],
    env_optional: list[str],
) -> dict[str, Any]:
    secret_keys = set(env_secret)
    env_lines = [
        "TEMP_MAIL_PROVIDER=",
        "EXTERNAL_POOL_DEFAULT_PROVIDER=auto",
        "ACTIVE_MAILBOX_PROVIDERS=",
        "# OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE=.runtime/providers.json",
    ]
    config_keys: list[str] = []
    _append_unique(config_keys, env_required)
    _append_unique(config_keys, env_optional)
    for key in config_keys:
        env_lines.append(f"{key}={_template_env_value(key, env_defaults, secret_keys)}")

    provider_config = {
        "providers": {
            "temp_mail_provider": "",
            "pool_default_provider": "auto",
            "active_mailbox_providers": [],
        }
    }
    provider_config_json = json.dumps(provider_config, ensure_ascii=False, indent=2)
    provider_config_toml = "\n".join(
        [
            "[providers]",
            'temp_mail_provider = ""',
            'pool_default_provider = "auto"',
            "active_mailbox_providers = []",
        ]
    )

    return {
        "priority": list(PROVIDER_SELECTION_SOURCE_PRIORITY),
        "env": {"format": "dotenv", "content": "\n".join(env_lines) + "\n"},
        "provider_config_json": {"format": "json", "content": provider_config_json + "\n"},
        "provider_config_toml": {"format": "toml", "content": provider_config_toml + "\n"},
        "provider_config_object": provider_config,
    }


def get_mailbox_provider_deployment_profile(
    catalog: list[dict[str, Any]] | None = None, *, strict: bool = True
) -> dict[str, Any]:
    source_catalog = catalog if catalog is not None else _build_mailbox_provider_catalog()
    active_names = _active_provider_names(strict=strict)
    alias_contract = get_provider_alias_contract()

    all_provider_values: list[str] = []
    active_provider_values: list[str] = []
    temp_runtime_values: list[str] = []
    temp_apply_values: list[str] = []
    pool_claim_values: list[str] = ["auto"]
    active_allowlist_values: list[str] = []

    env_required: list[str] = []
    env_optional: list[str] = []
    env_secret: list[str] = []
    env_defaults: dict[str, Any] = {}
    settings_keys: list[str] = []
    settings_required: list[str] = []
    settings_secret: list[str] = []
    settings_defaults: dict[str, Any] = {}
    provider_examples: dict[str, dict[str, Any]] = {}

    for item in source_catalog:
        provider = _normalize_provider_name(item.get("provider"))
        if not provider:
            continue
        kind = str(item.get("kind") or "").strip().lower()
        active = _catalog_item_active(item, active_names, strict=strict)
        deployment = item.get("deployment") if isinstance(item.get("deployment"), dict) else {}
        configuration = item.get("configuration") if isinstance(item.get("configuration"), dict) else {}
        selection = item.get("selection") if isinstance(item.get("selection"), dict) else {}

        _append_unique(all_provider_values, [provider])
        if active:
            _append_unique(active_provider_values, [provider])
        _append_unique(active_allowlist_values, [provider])
        if kind == "account" and str(item.get("account_type") or "").strip().lower() == "imap":
            _append_unique(active_allowlist_values, list(LEGACY_ACCOUNT_POOL_ALIASES))

        runtime_env = selection.get("runtime_env") if isinstance(selection.get("runtime_env"), dict) else {}
        runtime_provider = _normalize_provider_name(runtime_env.get(TEMP_MAIL_PROVIDER_ENV))
        temp_apply_provider = _normalize_provider_name(selection.get("temp_apply_provider_name"))
        pool_claim_provider = _normalize_provider_name(selection.get("pool_claim_provider"))
        if runtime_provider:
            _append_unique(temp_runtime_values, [runtime_provider])
        if temp_apply_provider:
            _append_unique(temp_apply_values, [temp_apply_provider])
        if pool_claim_provider:
            _append_unique(pool_claim_values, [pool_claim_provider])

        _append_unique(env_required, configuration.get("required_env") or [])
        _append_unique(env_optional, configuration.get("optional_env") or [])
        _append_unique(env_secret, configuration.get("secret_env") or [])
        _merge_defaults(env_defaults, configuration.get("env_defaults") or {})
        _append_unique(settings_keys, configuration.get("settings_keys") or [])
        _append_unique(settings_required, configuration.get("required_settings") or [])
        _append_unique(settings_secret, configuration.get("secret_settings") or [])
        _merge_defaults(settings_defaults, configuration.get("settings_defaults") or {})

        provider_examples[provider] = {
            "kind": kind,
            "label": item.get("label") or provider,
            "active": active,
            "activate": copy.deepcopy(deployment.get("activate") or {}),
            "runtime_default": copy.deepcopy(deployment.get("runtime_default") or {}),
            "pool_claim_default": copy.deepcopy(deployment.get("pool_claim_default") or {}),
            "pool_claim_request": copy.deepcopy(deployment.get("pool_claim_request") or {}),
            "task_temp_apply_request": copy.deepcopy(deployment.get("task_temp_apply_request") or {}),
            "required_env": list(configuration.get("required_env") or []),
            "optional_env": list(configuration.get("optional_env") or []),
            "secret_env": list(configuration.get("secret_env") or []),
            "env_defaults": copy.deepcopy(configuration.get("env_defaults") or {}),
            "required_settings": list(configuration.get("required_settings") or []),
            "settings_keys": list(configuration.get("settings_keys") or []),
            "secret_settings": list(configuration.get("secret_settings") or []),
            "settings_defaults": copy.deepcopy(configuration.get("settings_defaults") or {}),
            "configuration": {
                "required_env": list(configuration.get("required_env") or []),
                "optional_env": list(configuration.get("optional_env") or []),
                "secret_env": list(configuration.get("secret_env") or []),
                "env_defaults": copy.deepcopy(configuration.get("env_defaults") or {}),
                "required_settings": list(configuration.get("required_settings") or []),
                "settings_keys": list(configuration.get("settings_keys") or []),
                "secret_settings": list(configuration.get("secret_settings") or []),
                "settings_defaults": copy.deepcopy(configuration.get("settings_defaults") or {}),
            },
        }

    runtime_aliases = alias_contract.get("runtime_temp_mail_provider_aliases") or {}
    pool_aliases = alias_contract.get("pool_claim_provider_aliases") or {}
    _append_unique(temp_runtime_values, list(runtime_aliases.keys()))
    _append_unique(pool_claim_values, list(pool_aliases.keys()))
    _append_unique(active_allowlist_values, list(runtime_aliases.keys()))
    _append_unique(active_allowlist_values, list(pool_aliases.keys()))

    profile = {
        "version": 1,
        "env": copy.deepcopy(DEPLOYMENT_ENV_CONTRACT),
        "config_file": config.get_provider_config_file_status(),
        "templates": _deployment_profile_templates(
            env_defaults=env_defaults,
            env_secret=env_secret,
            env_required=env_required,
            env_optional=env_optional,
        ),
        "provider_values": {
            "all": all_provider_values,
            "active": active_provider_values,
            "active_allowlist": active_allowlist_values,
            "temp_runtime": temp_runtime_values,
            "temp_apply": temp_apply_values,
            "pool_claim": pool_claim_values,
        },
        "config_env": {
            "required": env_required,
            "optional": env_optional,
            "secret": env_secret,
            "defaults": env_defaults,
        },
        "config_settings": {
            "keys": settings_keys,
            "required": settings_required,
            "secret": settings_secret,
            "defaults": settings_defaults,
        },
        "aliases": copy.deepcopy(alias_contract),
        "provider_examples": provider_examples,
    }
    from .selection import get_mailbox_provider_selection_policy

    selection_policy = get_mailbox_provider_selection_policy(deployment_profile=profile)
    profile.update(
        {
            "selection_recipes": copy.deepcopy(selection_policy.get("selection_recipes") or []),
            "selection_recipe_index": copy.deepcopy(selection_policy.get("selection_recipe_index") or {}),
        }
    )
    return profile


def _available_temp_provider_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for item in get_available_providers():
        name = str(item.get("name") or "").strip()
        label = str(item.get("label") or "").strip()
        if name and label:
            labels[name] = label
    return labels


def _normalize_provider_name(value: Any) -> str:
    return str(value or "").strip().lower()


def _active_provider_names(*, strict: bool = True) -> set[str]:
    return settings_repo.get_active_mailbox_provider_name_set(strict=strict)


def _active_filter_enabled(*, strict: bool = True) -> bool:
    return bool(_active_provider_names(strict=strict))


def _active_matches_gptmail_family(provider_name: str, active_names: set[str]) -> bool:
    """Return True when a GPTMail catalog key is allowlisted.

    Dual-register keys (``custom_domain_temp_mail`` / ``legacy_bridge``) and
    runtime aliases (``gptmail`` / ``legacy_gptmail`` / ``temp_mail``) are one
    operator family. Allowlisting any member must keep both catalog keys active
    so stored inventory sources do not go inactive when only the twin key is
    listed in ACTIVE_MAILBOX_PROVIDERS.
    """
    normalized_provider = _normalize_provider_name(provider_name)
    pool_names = set(GPTMAIL_POOL_TEMP_PROVIDER_NAMES)
    if normalized_provider not in pool_names:
        return False
    family = pool_names.union(GPTMAIL_RUNTIME_ALIASES)
    return bool(set(active_names or ()).intersection(family))


def _catalog_item_active(item: dict[str, Any], active_names: set[str] | None = None, *, strict: bool = True) -> bool:
    active_names = _active_provider_names(strict=strict) if active_names is None else active_names
    if not active_names:
        return True

    provider = _normalize_provider_name(item.get("provider"))
    if not provider:
        return False
    if provider in active_names:
        return True
    if item.get("kind") == "account" and "imap" in active_names:
        return str(item.get("account_type") or "").strip().lower() == "imap"
    if item.get("kind") == "temp" and _active_matches_gptmail_family(provider, active_names):
        return True
    return False


def get_active_mailbox_provider_filter_contract(*, strict: bool = True) -> dict[str, Any]:
    active_names = settings_repo.get_active_mailbox_provider_names(strict=strict)
    active_override = config.get_active_mailbox_providers_override_info(strict=strict)
    catalog = _build_mailbox_provider_catalog()
    canonical_providers = {
        _normalize_provider_name(item.get("provider")) for item in catalog if _normalize_provider_name(item.get("provider"))
    }
    account_provider_aliases = {"imap"}
    recognized_aliases = set(GPTMAIL_RUNTIME_ALIASES).union(account_provider_aliases)
    supported_providers = sorted(canonical_providers.union(recognized_aliases))
    unknown_providers = [
        name
        for name in active_names
        if _normalize_provider_name(name) not in canonical_providers
        and _normalize_provider_name(name) not in recognized_aliases
    ]
    return {
        "active": bool(active_names),
        "mode": "allowlist" if active_names else "all",
        "active_providers": active_names,
        "unknown_providers": unknown_providers,
        "supported_providers": supported_providers,
        "recognized_aliases": sorted(recognized_aliases),
        "env": ACTIVE_MAILBOX_PROVIDER_ENV,
        "source": active_override.get("source") or ("settings" if active_names else "default"),
        "config_file": config.get_provider_config_file_status(),
        "config_error_code": active_override.get("error_code") or "",
        "config_error": active_override.get("error") or "",
    }


def _catalog_provider_names_by_kind(catalog: list[dict[str, Any]]) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {"account": set(), "temp": set()}
    for item in catalog:
        kind = str(item.get("kind") or "").strip().lower()
        provider = _normalize_provider_name(item.get("provider"))
        if kind in names and provider:
            names[kind].add(provider)
    return names


def _catalog_provider_active(catalog: list[dict[str, Any]], kind: str, provider_name: str, active_names: set[str]) -> bool:
    normalized_kind = str(kind or "").strip().lower()
    normalized_provider = _normalize_provider_name(provider_name)
    for item in catalog:
        if str(item.get("kind") or "").strip().lower() != normalized_kind:
            continue
        if _normalize_provider_name(item.get("provider")) == normalized_provider:
            return _catalog_item_active(item, active_names)
    return False


def _pool_default_provider_active(
    catalog: list[dict[str, Any]],
    provider_value: str,
    kind: str,
    alias_info: dict[str, Any] | None,
    active_names: set[str],
) -> bool:
    if not active_names or provider_value == "auto":
        return True
    if kind in {"account", "temp"} and _catalog_provider_active(catalog, kind, provider_value, active_names):
        return True
    if provider_value == "imap":
        return any(
            str(item.get("kind") or "").strip().lower() == "account"
            and str(item.get("account_type") or "").strip().lower() == "imap"
            and _catalog_item_active(item, active_names)
            for item in catalog
        )
    if isinstance(alias_info, dict) and str(alias_info.get("kind") or "").strip().lower() == "temp_family":
        temp_provider_names = {_normalize_provider_name(item) for item in alias_info.get("temp_provider_names") or []}
        return any(
            str(item.get("kind") or "").strip().lower() == "temp"
            and _normalize_provider_name(item.get("provider")) in temp_provider_names
            and _catalog_item_active(item, active_names)
            for item in catalog
        )
    return provider_value in active_names


def _temp_mail_default_provider_diagnostic(catalog: list[dict[str, Any]], *, strict: bool = True) -> dict[str, Any]:
    provider_override = config.get_temp_mail_provider_override_info(strict=strict)
    override_value = str(provider_override.get("value") or "").strip()
    provider_override_source = str(provider_override.get("source") or "")
    if override_value or provider_override_source == "config_file_error":
        source = provider_override_source or "env"
        key = str(provider_override.get("key") or TEMP_MAIL_PROVIDER_ENV)
        if provider_override_source == "config_file_error" and not override_value:
            stored_provider = settings_repo.get_setting("temp_mail_provider", "").strip()
            raw_provider = stored_provider or settings_repo.DEFAULT_TEMP_MAIL_PROVIDER
            fallback_source = "settings" if stored_provider else "default"
            fallback_key = "temp_mail_provider"
        else:
            raw_provider = override_value
            fallback_source = ""
            fallback_key = ""
    else:
        stored_provider = settings_repo.get_setting("temp_mail_provider", "").strip()
        if stored_provider:
            raw_provider = stored_provider
            source = "settings"
        else:
            raw_provider = settings_repo.DEFAULT_TEMP_MAIL_PROVIDER
            source = "default"
        key = "temp_mail_provider"
        fallback_source = ""
        fallback_key = ""

    provider_names = _catalog_provider_names_by_kind(catalog)["temp"]
    active_names = _active_provider_names(strict=strict)
    normalized_provider = _normalize_provider_name(settings_repo.normalize_temp_mail_provider_name(raw_provider))
    operator_provider = _canonical_bridge_operator_provider(normalized_provider)
    # Full catalog still dual-registers bridge keys; operator projection uses the
    # collapsed key so defaults match diagnostics/guide provider lists.
    valid = normalized_provider in provider_names or operator_provider in provider_names
    active_lookup = normalized_provider if normalized_provider in provider_names else operator_provider
    active = valid and _catalog_provider_active(catalog, "temp", active_lookup, active_names)
    diagnostic: dict[str, Any] = {
        "kind": "temp",
        "source": source,
        "key": key,
        "provider": operator_provider if valid else normalized_provider,
        "raw_provider": raw_provider,
        "valid": valid,
        "active": active,
        "canonical_provider": operator_provider if valid else None,
    }
    if source == "env":
        diagnostic["env"] = key
    elif source == "config_file":
        diagnostic["config_file"] = config.get_provider_config_file_status()
        diagnostic["config_key"] = key
    elif source == "config_file_error":
        diagnostic["config_file"] = provider_override.get("config_file") or config.get_provider_config_file_status()
        diagnostic["config_key"] = key
        diagnostic["config_error_code"] = provider_override.get("error_code") or "PROVIDER_CONFIG_FILE_INVALID"
        diagnostic["config_error"] = provider_override.get("error") or "Provider config file is invalid"
        diagnostic["fallback_source"] = fallback_source
        diagnostic["fallback_key"] = fallback_key
    else:
        diagnostic["settings_key"] = key
    if not valid:
        diagnostic["unknown_provider"] = normalized_provider
    elif not active:
        diagnostic["inactive_reason"] = "not_in_active_allowlist"
    return diagnostic


def _pool_claim_default_provider_diagnostic(catalog: list[dict[str, Any]], *, strict: bool = True) -> dict[str, Any]:
    provider_override = config.get_external_pool_default_provider_override_info(strict=strict)
    override_value = str(provider_override.get("value") or "").strip()
    provider_override_source = str(provider_override.get("source") or "")
    if override_value or provider_override_source == "config_file_error":
        source = provider_override_source or "env"
        key = str(provider_override.get("key") or EXTERNAL_POOL_DEFAULT_PROVIDER_ENV)
        if provider_override_source == "config_file_error" and not override_value:
            stored_provider = settings_repo.get_setting("pool_default_provider", "").strip()
            raw_provider = stored_provider or "auto"
            fallback_source = "settings" if stored_provider else "default"
            fallback_key = "pool_default_provider"
        else:
            raw_provider = override_value
            fallback_source = ""
            fallback_key = ""
    else:
        stored_provider = settings_repo.get_setting("pool_default_provider", "").strip()
        if stored_provider:
            raw_provider = stored_provider
            source = "settings"
        else:
            raw_provider = "auto"
            source = "default"
        key = "pool_default_provider"
        fallback_source = ""
        fallback_key = ""

    provider_names_by_kind = _catalog_provider_names_by_kind(catalog)
    catalog_provider_names = provider_names_by_kind["account"].union(provider_names_by_kind["temp"])
    alias_contract = get_provider_alias_contract().get("pool_claim_provider_aliases") or {}
    alias_names = {_normalize_provider_name(name) for name in alias_contract.keys()}
    active_names = _active_provider_names(strict=strict)
    normalized_provider = _normalize_provider_name(raw_provider)
    provider_value = normalized_provider or "auto"
    valid = provider_value == "auto" or provider_value in catalog_provider_names or provider_value in alias_names
    alias_info = alias_contract.get(provider_value) if isinstance(alias_contract, dict) else None
    canonical_provider: str | None = None
    kind = "auto"
    if provider_value in catalog_provider_names:
        canonical_provider = provider_value
        kind = "account" if provider_value in provider_names_by_kind["account"] else "temp"
    elif isinstance(alias_info, dict):
        canonical_value = alias_info.get("canonical_provider")
        canonical_provider = _normalize_provider_name(canonical_value) or None
        kind = str(alias_info.get("kind") or "alias").strip().lower()
    elif provider_value == "auto":
        kind = "auto"
    else:
        kind = "unknown"

    active = valid and _pool_default_provider_active(catalog, provider_value, kind, alias_info, active_names)

    diagnostic: dict[str, Any] = {
        "kind": kind,
        "source": source,
        "key": key,
        "provider": provider_value,
        "raw_provider": raw_provider,
        "valid": valid,
        "active": active,
        "canonical_provider": canonical_provider,
    }
    if source == "env":
        diagnostic["env"] = key
    elif source == "config_file":
        diagnostic["config_file"] = config.get_provider_config_file_status()
        diagnostic["config_key"] = key
    elif source == "config_file_error":
        diagnostic["config_file"] = provider_override.get("config_file") or config.get_provider_config_file_status()
        diagnostic["config_key"] = key
        diagnostic["config_error_code"] = provider_override.get("error_code") or "PROVIDER_CONFIG_FILE_INVALID"
        diagnostic["config_error"] = provider_override.get("error") or "Provider config file is invalid"
        diagnostic["fallback_source"] = fallback_source
        diagnostic["fallback_key"] = fallback_key
    else:
        diagnostic["settings_key"] = key
    if not valid:
        diagnostic["unknown_provider"] = provider_value
    elif not active:
        diagnostic["inactive_reason"] = "not_in_active_allowlist"
    return diagnostic


def get_mailbox_provider_default_diagnostics(
    catalog: list[dict[str, Any]] | None = None, *, strict: bool = True
) -> dict[str, Any]:
    source_catalog = catalog if catalog is not None else _build_mailbox_provider_catalog()
    temp_default = _temp_mail_default_provider_diagnostic(source_catalog, strict=strict)
    pool_default = _pool_claim_default_provider_diagnostic(source_catalog, strict=strict)
    invalid_defaults = [item for item in (temp_default, pool_default) if not item.get("valid")]
    inactive_defaults = [item for item in (temp_default, pool_default) if item.get("valid") and not item.get("active")]
    return {
        "temp_mail_provider": temp_default,
        "pool_claim_provider": pool_default,
        "invalid_defaults": invalid_defaults,
        "inactive_defaults": inactive_defaults,
    }


def get_active_account_provider_names() -> set[str] | None:
    active_names = _active_provider_names()
    if not active_names:
        return None
    return {
        _normalize_provider_name(item.get("provider"))
        for item in _build_mailbox_provider_catalog()
        if item.get("kind") == "account"
        and _normalize_provider_name(item.get("provider")) != "auto"
        and _catalog_item_active(item, active_names)
    }


def get_active_temp_provider_names() -> set[str] | None:
    active_names = _active_provider_names()
    if not active_names:
        return None
    return {
        _normalize_provider_name(item.get("provider"))
        for item in _build_mailbox_provider_catalog()
        if item.get("kind") == "temp" and _catalog_item_active(item, active_names)
    }


def is_mailbox_provider_active(kind: str, provider_name: str | None) -> bool:
    active_names = _active_provider_names()
    if not active_names:
        return True
    normalized_kind = str(kind or "").strip().lower()
    normalized_provider = _normalize_provider_name(provider_name)
    for item in _build_mailbox_provider_catalog():
        if item.get("kind") != normalized_kind:
            continue
        if _normalize_provider_name(item.get("provider")) == normalized_provider:
            return _catalog_item_active(item, active_names)
    if normalized_kind == "temp" and normalized_provider in GPTMAIL_RUNTIME_ALIASES:
        # Runtime aliases are active when any bridge family member is allowlisted.
        family = set(GPTMAIL_POOL_TEMP_PROVIDER_NAMES).union(GPTMAIL_RUNTIME_ALIASES)
        return bool(active_names.intersection(family))
    if normalized_kind == "temp" and normalized_provider in set(GPTMAIL_POOL_TEMP_PROVIDER_NAMES):
        return _active_matches_gptmail_family(normalized_provider, active_names)
    return normalized_provider in active_names


def temp_mail_provider_label(provider_name: str | None) -> str:
    name = _normalize_provider_name(provider_name)
    if not name:
        return _TEMP_PROVIDER_LABEL_OVERRIDES["custom_domain_temp_mail"]
    if name in _TEMP_PROVIDER_LABEL_OVERRIDES:
        return _TEMP_PROVIDER_LABEL_OVERRIDES[name]
    available_labels = _available_temp_provider_labels()
    if name in available_labels:
        return available_labels[name]
    return _TEMP_PROVIDER_LABEL_OVERRIDES.get(name, str(provider_name or "").strip() or "Temp Mail")


def temp_mail_provider_display_label(provider_name: str | None, *, locale: str = "en") -> str:
    name = _normalize_provider_name(provider_name)
    if str(locale or "").strip().lower().startswith("zh") and name in _TEMP_PROVIDER_ZH_LABEL_OVERRIDES:
        return _TEMP_PROVIDER_ZH_LABEL_OVERRIDES[name]
    return temp_mail_provider_label(provider_name)


def temp_mail_provider_config_status(provider_name: str | None) -> dict[str, Any]:
    name = _normalize_provider_name(provider_name)
    missing: list[str] = []
    available_temp_providers = {
        str(item.get("name") or "").strip(): item for item in get_available_providers() if str(item.get("name") or "").strip()
    }

    if name in {"custom_domain_temp_mail", "legacy_bridge", "legacy_gptmail", "gptmail", "temp_mail"}:
        if not settings_repo.get_temp_mail_api_base_url():
            missing.append("temp_mail_api_base_url")
        if not settings_repo.get_temp_mail_api_key():
            missing.append("temp_mail_api_key")
    elif name == "cloudflare_temp_mail":
        if not settings_repo.get_cf_worker_base_url():
            missing.append("cf_worker_base_url")
        if not settings_repo.get_cf_worker_admin_key():
            missing.append("cf_worker_admin_key")
    elif name == "duckmail":
        if not settings_repo.get_duckmail_api_base():
            missing.append("duckmail_api_base")
        if not settings_repo.get_duckmail_bearer_token():
            missing.append("duckmail_bearer_token")
    elif name == "emailnator":
        if not settings_repo.get_emailnator_api_key():
            missing.append("emailnator_api_key")
    elif name in {"mail_tm", "tempmail_lol"}:
        missing = []
    elif name in available_temp_providers:
        return _plugin_provider_config_status(name, available_temp_providers[name])
    else:
        missing.append("temp_mail_provider")

    return {"configured": not missing, "missing_config": missing}


def _build_mailbox_provider_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for item in get_provider_list():
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        account_type = str(item.get("account_type") or "imap").strip().lower()
        if key == "auto":
            read_capability = "mixed"
        elif account_type == "outlook":
            read_capability = "graph"
        else:
            read_capability = "imap"
        note = str(item.get("note") or "").strip()
        catalog_item = {
            "kind": "account",
            "provider": key,
            "label": item.get("label") or key,
            "account_type": account_type,
            "read_capability": read_capability,
            "can_send": False,
            "can_delete_mailbox": False,
            "can_delete_message": False,
            "can_clear_messages": False,
            "config_source": "builtin",
            "configured": True,
            "missing_config": [],
            "requires_pool_inventory": True,
            "can_dynamic_create": False,
            "selection": _account_provider_selection_contract(key),
            "configuration": _account_provider_configuration_contract(key, account_type),
        }
        if note:
            catalog_item["note"] = note
        catalog_item["deployment"] = _provider_deployment_contract(catalog_item)
        catalog.append(catalog_item)

    for item in get_available_providers():
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        capabilities = normalize_provider_capabilities(item.get("capabilities"))
        from .constants import _CORE_BUILTIN_TEMP_PROVIDERS

        is_core_builtin_temp_provider = name in _CORE_BUILTIN_TEMP_PROVIDERS
        # Installed official plugins still use shared settings keys / contracts.
        if name in _TEMP_PROVIDER_CONFIG_CONTRACTS:
            config_status = temp_mail_provider_config_status(name)
        elif is_core_builtin_temp_provider:
            config_status = temp_mail_provider_config_status(name)
        else:
            config_status = _plugin_provider_config_status(name, item)
        configuration = _temp_provider_configuration_contract(name, item)
        catalog_item = {
            "kind": "temp",
            "provider": name,
            "label": temp_mail_provider_label(name),
            "read_capability": "temp_provider",
            "can_send": False,
            "can_delete_mailbox": bool(capabilities.get("delete_mailbox")),
            "can_delete_message": bool(capabilities.get("delete_message")),
            "can_clear_messages": bool(capabilities.get("clear_messages")),
            "config_source": "builtin" if is_core_builtin_temp_provider else "plugin",
            "configured": bool(config_status["configured"]),
            "missing_config": list(config_status["missing_config"]),
            "requires_pool_inventory": False,
            "can_dynamic_create": True,
            "selection": _temp_provider_selection_contract(name),
            "configuration": configuration,
            "settings_ui": _temp_provider_settings_ui_contract(name, configuration, item),
            "version": item.get("version") or "0.0.0",
            "author": item.get("author") or "",
            "contract_validation": copy.deepcopy(item.get("contract_validation") or {}),
        }
        catalog_item["deployment"] = _provider_deployment_contract(catalog_item)
        catalog.append(catalog_item)
    return catalog


def get_mailbox_provider_catalog(*, include_inactive: bool = False, strict: bool = True) -> list[dict[str, Any]]:
    catalog = _build_mailbox_provider_catalog()
    active_names = _active_provider_names(strict=strict)
    if include_inactive or not active_names:
        return [dict(item) | {"active": _catalog_item_active(item, active_names, strict=strict)} for item in catalog]
    return [dict(item) | {"active": True} for item in catalog if _catalog_item_active(item, active_names, strict=strict)]


def _provider_readiness_status(item: dict[str, Any]) -> str:
    if not bool(item.get("active", True)):
        return "inactive"
    if not bool(item.get("configured", True)):
        return "needs_config"
    return "ready"


def _provider_readiness_reason(item: dict[str, Any], status: str) -> str:
    if status == "inactive":
        return "not_in_active_allowlist"
    if status == "needs_config":
        return "missing_config"
    return "local_config_ready"


def _provider_diagnostic_item(item: dict[str, Any]) -> dict[str, Any]:
    configuration = item.get("configuration") if isinstance(item.get("configuration"), dict) else {}
    status = _provider_readiness_status(item)
    diagnostic = {
        "kind": item.get("kind") or "",
        "provider": item.get("provider") or "",
        "label": item.get("label") or item.get("provider") or "",
        "active": bool(item.get("active", True)),
        "configured": bool(item.get("configured", True)),
        "status": status,
        "status_reason": _provider_readiness_reason(item, status),
        "missing_config": list(item.get("missing_config") or []),
        "read_capability": item.get("read_capability") or "",
        "config_source": item.get("config_source") or "builtin",
        "requires_pool_inventory": bool(item.get("requires_pool_inventory")),
        "can_dynamic_create": bool(item.get("can_dynamic_create")),
        "required_env": list(configuration.get("required_env") or []),
        "optional_env": list(configuration.get("optional_env") or []),
        "required_settings": list(configuration.get("required_settings") or []),
        "settings_keys": list(configuration.get("settings_keys") or []),
        "secret_env": list(configuration.get("secret_env") or []),
        "secret_settings": list(configuration.get("secret_settings") or []),
        "selection": copy.deepcopy(item.get("selection") or {}),
        "deployment": copy.deepcopy(item.get("deployment") or {}),
        "contract_validation": copy.deepcopy(item.get("contract_validation") or {}),
    }
    if item.get("account_type"):
        diagnostic["account_type"] = item.get("account_type")
    if item.get("version"):
        diagnostic["version"] = item.get("version")
    if item.get("author"):
        diagnostic["author"] = item.get("author")
    return diagnostic


def get_mailbox_provider_diagnostics(*, include_inactive: bool = True) -> dict[str, Any]:
    """Return local readiness diagnostics for every mailbox provider.

    This intentionally does not probe upstream networks. It only reflects the
    active allowlist and local/env-backed configuration state used by runtime
    provider selection.

    GPTMail dual-register keys are collapsed to
    ``legacy_bridge`` so operator/API summaries do not double-count the same
    bridge implementation. Full catalog lookup still returns both registry names.
    """
    providers = _collapse_bridge_operator_provider_rows(
        [
            _provider_diagnostic_item(item)
            for item in get_mailbox_provider_catalog(include_inactive=include_inactive, strict=False)
        ]
    )
    default_diagnostics = get_mailbox_provider_default_diagnostics(_build_mailbox_provider_catalog(), strict=False)
    provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    summary = {
        "total": len(providers),
        "active": 0,
        "inactive": 0,
        "ready": 0,
        "configured": 0,
        "needs_config": 0,
        "dynamic_create": 0,
        "account": 0,
        "temp": 0,
        "unknown_filter_entries": len(provider_filter.get("unknown_providers") or []),
        "invalid_default_entries": len(default_diagnostics.get("invalid_defaults") or []),
        "inactive_default_entries": len(default_diagnostics.get("inactive_defaults") or []),
    }
    for item in providers:
        kind = str(item.get("kind") or "").strip().lower()
        if kind in {"account", "temp"}:
            summary[kind] += 1
        if item.get("active"):
            summary["active"] += 1
            if item.get("configured"):
                summary["ready"] += 1
                summary["configured"] += 1
            else:
                summary["needs_config"] += 1
            if item.get("can_dynamic_create"):
                summary["dynamic_create"] += 1
        else:
            summary["inactive"] += 1

    return {
        "summary": summary,
        "filter": provider_filter,
        "defaults": default_diagnostics,
        "scope": {
            "type": "local_config",
            "network_probe": False,
            "description": "Provider readiness is based on local settings, environment variables, and the active allowlist.",
        },
        "providers": providers,
    }


def account_provider_label(provider_name: str | None) -> str:
    name = _normalize_provider_name(provider_name)
    if not name:
        return ""
    return str((MAIL_PROVIDERS.get(name, {}) or {}).get("label") or provider_name or "")


def mailbox_session_provider_metadata(source: dict[str, Any]) -> dict[str, str]:
    """Return secret-free provider display metadata for an account or temp-mail session source."""
    provider = str(source.get("provider") or source.get("provider_name") or "").strip()
    account_type = str(source.get("account_type") or "").strip().lower()
    if account_type == "temp_mail" or source.get("session_type") == "task_temp_mailbox":
        catalog_item = get_provider_catalog_item("temp", provider) or {}
        return {
            "provider": provider,
            "provider_label": str(catalog_item.get("label") or temp_mail_provider_label(provider)),
            "read_capability": str(catalog_item.get("read_capability") or "temp_provider"),
        }

    catalog_item = get_provider_catalog_item("account", provider) or {}
    return {
        "provider": provider,
        "provider_label": str(catalog_item.get("label") or account_provider_label(provider) or provider),
        "read_capability": str(catalog_item.get("read_capability") or ("imap" if account_type == "imap" else "graph")),
    }


def get_provider_catalog_item(
    kind: str, provider_name: str | None, *, include_inactive: bool = False
) -> dict[str, Any] | None:
    normalized_kind = str(kind or "").strip().lower()
    normalized_provider = _normalize_provider_name(provider_name)
    for item in get_mailbox_provider_catalog(include_inactive=include_inactive, strict=False):
        if item.get("kind") == normalized_kind and _normalize_provider_name(item.get("provider")) == normalized_provider:
            return dict(item)
    return None
