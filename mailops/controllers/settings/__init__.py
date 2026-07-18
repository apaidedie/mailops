"""Package facade — re-exports public symbols for stable imports."""

from __future__ import annotations

# Historical unittest.patch target: controllers.settings.config.*
from mailops import config

from .helpers import (
    _coerce_int_range,
    _ensure_email_service_available,
    _is_valid_notification_email,
    _json_error,
    _mask_secret_value,
    _parse_allowed_emails_input,
    _parse_bool_input,
    _parse_emailnator_email_types_input,
    _parse_mailbox_provider_list_input,
    _parse_temp_mail_domains_input,
    _parse_temp_mail_prefix_rules_input,
    _plugin_settings_contract,
)
from .read_api import (
    api_external_api_contract_check,
    api_get_external_api_key_plaintext,
    api_get_settings,
)
from .test_api import (
    api_sync_cf_worker_domains,
    api_test_email,
    api_test_telegram,
    api_test_telegram_proxy,
    api_test_verification_ai,
    api_test_webhook,
    api_validate_cron,
)
from .update_api import (
    api_update_settings,
)

__all__ = [
    "config",
    "_mask_secret_value",
    "_plugin_settings_contract",
    "_parse_allowed_emails_input",
    "_parse_bool_input",
    "_coerce_int_range",
    "_parse_temp_mail_domains_input",
    "_parse_temp_mail_prefix_rules_input",
    "_parse_emailnator_email_types_input",
    "_parse_mailbox_provider_list_input",
    "_is_valid_notification_email",
    "_json_error",
    "_ensure_email_service_available",
    "api_get_settings",
    "api_get_external_api_key_plaintext",
    "api_external_api_contract_check",
    "api_update_settings",
    "api_validate_cron",
    "api_test_email",
    "api_test_webhook",
    "api_test_verification_ai",
    "api_sync_cf_worker_domains",
    "api_test_telegram",
    "api_test_telegram_proxy",
]
