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

# Operator-facing product name for the built-in GPTMail-compatible temp provider.
# Internal keys remain legacy_bridge / custom_domain_temp_mail / gptmail for storage compat.
GPTMAIL_PROVIDER_LABEL = "GPTMail"
GPTMAIL_PROVIDER_LABEL_ZH = "GPTMail"
# Historical constant names kept as aliases so older imports keep working.
COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL = GPTMAIL_PROVIDER_LABEL
COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL_ZH = GPTMAIL_PROVIDER_LABEL_ZH

# Only Cloudflare is a true built-in. GPTMail and public services install as plugins.
_CORE_BUILTIN_TEMP_PROVIDERS = frozenset(
    {
        "cloudflare_temp_mail",
    }
)

_TEMP_PROVIDER_LABEL_OVERRIDES = {
    "custom_domain_temp_mail": GPTMAIL_PROVIDER_LABEL,
    "legacy_bridge": GPTMAIL_PROVIDER_LABEL,
    "legacy_gptmail": GPTMAIL_PROVIDER_LABEL,
    "gptmail": GPTMAIL_PROVIDER_LABEL,
    "temp_mail": GPTMAIL_PROVIDER_LABEL,
    "cloudflare_temp_mail": "Cloudflare Temp Mail",
    "mail_tm": "Mail.tm",
    "duckmail": "DuckMail",
    "tempmail_lol": "TempMail.lol",
    "emailnator": "Emailnator",
}

_TEMP_PROVIDER_ZH_LABEL_OVERRIDES = {
    "custom_domain_temp_mail": GPTMAIL_PROVIDER_LABEL_ZH,
    "legacy_bridge": GPTMAIL_PROVIDER_LABEL_ZH,
    "legacy_gptmail": GPTMAIL_PROVIDER_LABEL_ZH,
    "gptmail": GPTMAIL_PROVIDER_LABEL_ZH,
    "temp_mail": GPTMAIL_PROVIDER_LABEL_ZH,
}

GPTMAIL_POOL_TEMP_PROVIDER_NAMES = ("custom_domain_temp_mail", "legacy_bridge")
GPTMAIL_RUNTIME_ALIASES = ("gptmail", "legacy_gptmail", "temp_mail")
# Operator/API projection collapses GPTMail dual-register keys.
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
