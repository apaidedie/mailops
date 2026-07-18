"""Compatibility hub for provider_catalog domains.

Prefer importing public symbols from ``mailops.services.provider_catalog``.
This module re-exports domain implementations so older ``from ._impl import ...``
and monkeypatches on package attributes continue to work.
"""

from __future__ import annotations

from .bridge import (  # noqa: F401
    _canonical_bridge_operator_provider,
    _collapse_bridge_operator_provider_rows,
    _merge_unique_str_list,
    get_operator_temp_mail_default_provider,
)
from .capabilities import (  # noqa: F401
    get_external_api_capabilities_contract,
    get_external_api_integration_bundle,
    get_external_api_readiness_summary,
)
from .catalog import (  # noqa: F401
    _active_provider_names,
    _normalize_provider_name,
    _provider_diagnostic_item,
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
from .constants import (  # noqa: F401
    _BRIDGE_OPERATOR_CANONICAL,
    _BRIDGE_OPERATOR_FAMILY,
    _TEMP_PROVIDER_LABEL_OVERRIDES,
    _TEMP_PROVIDER_ZH_LABEL_OVERRIDES,
    ACTIVE_MAILBOX_PROVIDER_ENV,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_API_LEGACY_PREFIX,
    EXTERNAL_API_V1_PREFIX,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    GPTMAIL_POOL_TEMP_PROVIDER_NAMES,
    GPTMAIL_RUNTIME_ALIASES,
    LEGACY_ACCOUNT_POOL_ALIASES,
    PROVIDER_SELECTION_SOURCE_PRIORITY,
    TEMP_MAIL_PROVIDER_ENV,
)
from .endpoints import (  # noqa: F401
    _CANONICAL_EXTERNAL_ENDPOINTS,
    _EXTERNAL_ACTION_ENDPOINT_KEYS,
    _EXTERNAL_MAILBOX_SESSION_CLOSE_ACTION,
    _EXTERNAL_MAILBOX_SESSION_READ_ACTION,
    _EXTERNAL_POOL_LIFECYCLE_ACTIONS,
    _EXTERNAL_READ_ACTIONS,
    _EXTERNAL_TASK_TEMP_ACTIONS,
    _LEGACY_EXTERNAL_ENDPOINTS,
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
from .health import (  # noqa: F401
    get_mailbox_provider_health,
    get_mailbox_provider_preflight,
)
from .integration import (  # noqa: F401
    _integration_manifest_workflows,
    get_external_integration_manifest,
    get_mailbox_directory_provider_context,
    get_mailbox_provider_readiness_summary,
    get_provider_integration_guide,
)
from .selection import get_mailbox_provider_selection_policy  # noqa: F401
