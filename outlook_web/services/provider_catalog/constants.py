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


COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL = "Compatible Temp Mail Bridge"
COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH = "兼容临时邮箱桥接"

_TEMP_PROVIDER_LABEL_OVERRIDES = {
    "custom_domain_temp_mail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    "legacy_bridge": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    "legacy_gptmail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    "gptmail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    "temp_mail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
    "cloudflare_temp_mail": "Cloudflare Temp Mail",
    "mail_tm": "Mail.tm",
    "duckmail": "DuckMail",
    "tempmail_lol": "TempMail.lol",
    "emailnator": "Emailnator",
}

_TEMP_PROVIDER_ZH_LABEL_OVERRIDES = {
    "custom_domain_temp_mail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    "legacy_bridge": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    "legacy_gptmail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    "gptmail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
    "temp_mail": COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH,
}

GPTMAIL_POOL_TEMP_PROVIDER_NAMES = ("custom_domain_temp_mail", "legacy_bridge")
GPTMAIL_RUNTIME_ALIASES = ("gptmail", "legacy_gptmail", "temp_mail")
# Operator/API projection collapses Compatible Temp Mail Bridge dual-register keys.
# Registry + full catalog still keep both names for stored-source compatibility.
_BRIDGE_OPERATOR_CANONICAL = settings_repo.LEGACY_TEMP_MAIL_PROVIDER
_BRIDGE_OPERATOR_FAMILY = frozenset(
    {
        "custom_domain_temp_mail",
        "legacy_bridge",
        *GPTMAIL_RUNTIME_ALIASES,
    }
)
LEGACY_ACCOUNT_POOL_ALIASES = ("imap",)
ACTIVE_MAILBOX_PROVIDER_ENV = "ACTIVE_MAILBOX_PROVIDERS"
TEMP_MAIL_PROVIDER_ENV = "TEMP_MAIL_PROVIDER"
EXTERNAL_POOL_DEFAULT_PROVIDER_ENV = "EXTERNAL_POOL_DEFAULT_PROVIDER"
EXTERNAL_API_LEGACY_PREFIX = "/api/external"  # removed in W2; migration reference only
EXTERNAL_API_V1_PREFIX = "/api/v1/external"



DEPLOYMENT_ENV_CONTRACT = {
    "active_mailbox_providers": ACTIVE_MAILBOX_PROVIDER_ENV,
    "pool_claim_provider": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    "temp_mail_provider": TEMP_MAIL_PROVIDER_ENV,
}

PROVIDER_SELECTION_SOURCE_PRIORITY = ["env", "provider_config_file", "settings", "default"]
