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

from .catalog import (
    _provider_selection_recipe_bundle,
    get_mailbox_provider_deployment_profile,
)
from .constants import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    PROVIDER_SELECTION_SOURCE_PRIORITY,
    TEMP_MAIL_PROVIDER_ENV,
)
from .endpoints import _CANONICAL_EXTERNAL_ENDPOINTS


def get_mailbox_provider_selection_policy(*, deployment_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the runtime policy for choosing mailbox providers.

    The values here mirror the actual settings/env/config-file resolution
    paths. It is intentionally separate from the provider list so external
    consumers can programmatically decide which field or deployment knob to
    use for each workflow without reverse-engineering several payload fields.
    """
    if deployment_profile is None:
        deployment_profile = get_mailbox_provider_deployment_profile()
    provider_values = deployment_profile.get("provider_values") or {}
    aliases = deployment_profile.get("aliases") or {}
    config_file_status = deployment_profile.get("config_file") or config.get_provider_config_file_status()

    policy = {
        "version": 1,
        "source_priority": list(PROVIDER_SELECTION_SOURCE_PRIORITY),
        "config_file": {
            **copy.deepcopy(config_file_status),
            "priority": "after_env_before_settings",
            "priority_slot": "provider_config_file",
            "diagnostic_source": "config_file",
            "supported_sections": ["mailbox_providers", "providers", "mailbox", "env"],
        },
        "scopes": {
            "active_allowlist": {
                "purpose": "Restrict which mailbox providers are exposed and used by catalog, pool claims, and task temp-mail creation.",
                "env": ACTIVE_MAILBOX_PROVIDER_ENV,
                "settings_key": "active_mailbox_providers",
                "config_keys": [ACTIVE_MAILBOX_PROVIDER_ENV, "active_mailbox_providers", "active_providers"],
                "value_format": "comma_or_newline_list_or_json_array",
                "empty_value": "all_providers_active",
                "allowed_values": list(provider_values.get("active_allowlist") or []),
            },
            "temp_runtime_default": {
                "purpose": "Choose the default provider used by app-side temp-mail generation when a request does not pass provider_name.",
                "env": TEMP_MAIL_PROVIDER_ENV,
                "settings_key": "temp_mail_provider",
                "config_keys": [TEMP_MAIL_PROVIDER_ENV, "temp_mail_provider", "runtime_temp_mail_provider"],
                "request_field": "provider_name",
                "allowed_values": list(provider_values.get("temp_runtime") or []),
                "aliases": copy.deepcopy(aliases.get("runtime_temp_mail_provider_aliases") or {}),
            },
            "pool_claim_default": {
                "purpose": "Choose the default provider for external pool claim-random when the request omits provider.",
                "env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
                "settings_key": "pool_default_provider",
                "config_keys": [
                    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
                    "pool_default_provider",
                    "pool_claim_provider",
                    "external_pool_default_provider",
                ],
                "request_field": "provider",
                "allowed_values": list(provider_values.get("pool_claim") or []),
                "empty_value": "auto",
                "aliases": copy.deepcopy(aliases.get("pool_claim_provider_aliases") or {}),
            },
            "task_temp_apply": {
                "purpose": "Choose the provider for task-scoped temp-mail creation through the external API.",
                "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["temp_mail_apply"],
                "request_field": "provider_name",
                "allowed_values": list(provider_values.get("temp_apply") or []),
            },
            "explicit_pool_claim": {
                "purpose": "Choose a provider for one external pool claim-random request.",
                "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_random"],
                "request_field": "provider",
                "allowed_values": list(provider_values.get("pool_claim") or []),
            },
        },
        "templates": copy.deepcopy(deployment_profile.get("templates") or {}),
    }
    recipes = _provider_selection_recipe_bundle(
        deployment_profile=deployment_profile,
        selection_policy=policy,
    )
    policy.update(recipes)
    return policy
