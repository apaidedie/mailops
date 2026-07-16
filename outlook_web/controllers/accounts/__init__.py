"""Package facade — re-exports public symbols for stable imports."""

from __future__ import annotations

# Compatibility re-exports used by tests (logic lives in account_import_export).
from outlook_web.services.account_import_export import (  # noqa: E402
    _build_export_text,
    _detect_line_type,
)

from .batch import (
    api_batch_delete_accounts,
    api_batch_manage_tags,
    api_batch_notification_toggle,
    api_batch_update_account_group,
    api_batch_update_status,
)
from .crud import (
    api_add_account,
    api_delete_account,
    api_delete_account_by_email,
    api_update_account,
    api_update_account_remark,
)
from .export_api import (
    api_export_all_accounts,
    api_export_selected_accounts,
    api_generate_export_verify_token,
)
from .helpers import (
    _api_update_account_status,
    _build_account_import_failure_response,
    _handle_auto_import,
    _handle_temp_mail_import,
    _normalize_account_status,
    _overwrite_account,
    _parse_bool_flag,
    _resolve_auto_group,
    sanitize_input,
)
from .list_api import (
    api_get_account,
    api_get_accounts,
    api_get_provider_health,
    api_get_provider_preflight,
    api_get_providers,
    api_search_accounts,
)
from .refresh_api import (
    REFRESH_LOCK_NAME,
    api_get_account_refresh_logs,
    api_get_failed_refresh_logs,
    api_get_invalid_token_candidates,
    api_get_refresh_logs,
    api_get_refresh_stats,
    api_refresh_account,
    api_refresh_all_accounts,
    api_refresh_failed_accounts,
    api_refresh_selected_accounts,
    api_retry_refresh_account,
    api_trigger_scheduled_refresh,
)
from .telegram_api import (
    api_telegram_toggle,
)

__all__ = [
    "sanitize_input",
    "_parse_bool_flag",
    "_normalize_account_status",
    "_build_account_import_failure_response",
    "_resolve_auto_group",
    "_overwrite_account",
    "_handle_temp_mail_import",
    "_handle_auto_import",
    "_api_update_account_status",
    "api_get_accounts",
    "api_get_account",
    "api_get_providers",
    "api_get_provider_preflight",
    "api_get_provider_health",
    "api_search_accounts",
    "api_add_account",
    "api_update_account",
    "api_update_account_remark",
    "api_delete_account",
    "api_delete_account_by_email",
    "api_batch_update_status",
    "api_batch_notification_toggle",
    "api_batch_delete_accounts",
    "api_batch_manage_tags",
    "api_batch_update_account_group",
    "api_export_all_accounts",
    "api_export_selected_accounts",
    "api_generate_export_verify_token",
    "REFRESH_LOCK_NAME",
    "api_refresh_account",
    "api_refresh_all_accounts",
    "api_retry_refresh_account",
    "api_refresh_failed_accounts",
    "api_trigger_scheduled_refresh",
    "api_get_refresh_logs",
    "api_get_account_refresh_logs",
    "api_get_failed_refresh_logs",
    "api_get_invalid_token_candidates",
    "api_get_refresh_stats",
    "api_refresh_selected_accounts",
    "api_telegram_toggle",
    "_build_export_text",
    "_detect_line_type",
]
