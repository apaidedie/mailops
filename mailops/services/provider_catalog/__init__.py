"""Mailbox provider catalog and external API discovery contracts.

Stable public import path:
    from mailops.services.provider_catalog import get_mailbox_provider_catalog

Implementation lives in ``_impl`` (extracted domain modules may re-export from here).
"""

from __future__ import annotations

import sys
import types

from ._impl import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_API_LEGACY_PREFIX,
    EXTERNAL_API_V1_PREFIX,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    EXTERNAL_READ_ENDPOINTS,
    EXTERNAL_READ_QUERY_FIELDS,
    GPTMAIL_POOL_TEMP_PROVIDER_NAMES,
    GPTMAIL_RUNTIME_ALIASES,
    LEGACY_ACCOUNT_POOL_ALIASES,
    LEGACY_PROVIDER_HEALTH_ENDPOINT,
    LEGACY_PROVIDER_PREFLIGHT_ENDPOINT,
    MAILBOX_SESSION_CLOSE_ENDPOINT,
    MAILBOX_SESSION_READ_ENDPOINT,
    MAILBOX_SESSION_START_ENDPOINT,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    PROVIDER_SELECTION_SOURCE_PRIORITY,
    TEMP_MAIL_PROVIDER_ENV,
    _integration_manifest_workflows,
    _provider_selection_recipe_bundle,
    account_provider_label,
    get_active_account_provider_names,
    get_active_mailbox_provider_filter_contract,
    get_active_temp_provider_names,
    get_external_api_capabilities_contract,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_api_integration_bundle,
    get_external_api_legacy_endpoint_map,
    get_external_api_readiness_summary,
    get_external_integration_manifest,
    get_external_mailbox_read_contract,
    get_mailbox_directory_provider_context,
    get_mailbox_provider_catalog,
    get_mailbox_provider_default_diagnostics,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_mailbox_provider_health,
    get_mailbox_provider_preflight,
    get_mailbox_provider_readiness_summary,
    get_mailbox_provider_selection_policy,
    get_operator_temp_mail_default_provider,
    get_provider_alias_contract,
    get_provider_catalog_item,
    get_provider_documentation_contract,
    get_provider_integration_guide,
    is_mailbox_provider_active,
    mailbox_session_provider_metadata,
    temp_mail_provider_config_status,
    temp_mail_provider_display_label,
    temp_mail_provider_label,
)


class _ProviderCatalogModule(types.ModuleType):
    """Facade module that mirrors attribute writes onto ``_impl`` for monkeypatch tests."""

    def __getattr__(self, name: str):
        from . import _impl

        try:
            return getattr(_impl, name)
        except AttributeError as exc:
            raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}") from exc

    def __setattr__(self, name: str, value):
        super().__setattr__(name, value)
        if name.startswith("__"):
            return
        from . import (
            _impl,
            bridge,
            capabilities,
            catalog,
            endpoints,
            health,
            integration,
            selection,
        )

        for module in (
            _impl,
            bridge,
            catalog,
            selection,
            integration,
            capabilities,
            endpoints,
            health,
        ):
            if hasattr(module, name):
                setattr(module, name, value)

    def __dir__(self):
        from . import _impl

        return sorted(set(super().__dir__()) | set(dir(_impl)))


sys.modules[__name__].__class__ = _ProviderCatalogModule


__all__ = [
    "COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL",
    "COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH",
    "GPTMAIL_POOL_TEMP_PROVIDER_NAMES",
    "GPTMAIL_RUNTIME_ALIASES",
    "LEGACY_ACCOUNT_POOL_ALIASES",
    "ACTIVE_MAILBOX_PROVIDER_ENV",
    "TEMP_MAIL_PROVIDER_ENV",
    "EXTERNAL_POOL_DEFAULT_PROVIDER_ENV",
    "EXTERNAL_API_LEGACY_PREFIX",
    "EXTERNAL_API_V1_PREFIX",
    "PROVIDER_HEALTH_ENDPOINT",
    "PROVIDER_PREFLIGHT_ENDPOINT",
    "LEGACY_PROVIDER_HEALTH_ENDPOINT",
    "LEGACY_PROVIDER_PREFLIGHT_ENDPOINT",
    "DEPLOYMENT_ENV_CONTRACT",
    "PROVIDER_SELECTION_SOURCE_PRIORITY",
    "EXTERNAL_READ_ENDPOINTS",
    "MAILBOX_SESSION_START_ENDPOINT",
    "MAILBOX_SESSION_READ_ENDPOINT",
    "MAILBOX_SESSION_CLOSE_ENDPOINT",
    "EXTERNAL_READ_QUERY_FIELDS",
    "get_operator_temp_mail_default_provider",
    "get_external_api_endpoint_map",
    "get_external_api_legacy_endpoint_map",
    "get_external_api_compatibility_contract",
    "get_provider_documentation_contract",
    "get_external_mailbox_read_contract",
    "get_mailbox_provider_selection_policy",
    "get_provider_integration_guide",
    "get_mailbox_provider_readiness_summary",
    "get_external_integration_manifest",
    "get_mailbox_directory_provider_context",
    "get_external_api_capabilities_contract",
    "get_external_api_readiness_summary",
    "get_external_api_integration_bundle",
    "get_provider_alias_contract",
    "get_mailbox_provider_deployment_profile",
    "get_active_mailbox_provider_filter_contract",
    "get_mailbox_provider_default_diagnostics",
    "get_active_account_provider_names",
    "get_active_temp_provider_names",
    "is_mailbox_provider_active",
    "temp_mail_provider_label",
    "temp_mail_provider_display_label",
    "temp_mail_provider_config_status",
    "get_mailbox_provider_catalog",
    "get_mailbox_provider_diagnostics",
    "account_provider_label",
    "mailbox_session_provider_metadata",
    "get_provider_catalog_item",
    "get_mailbox_provider_preflight",
    "get_mailbox_provider_health",
]
