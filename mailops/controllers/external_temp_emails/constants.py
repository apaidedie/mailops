from __future__ import annotations

import copy
from typing import Any

from flask import jsonify, request

from mailops.repositories import settings as settings_repo
from mailops.security.auth import api_key_required, get_external_api_consumer
from mailops.security.external_api_guard import check_feature_enabled, external_api_guards
from mailops.services import external_api as external_api_service
from mailops.services.external_request_limits import CALLER_ID_MAX_LEN, DETAIL_MAX_LEN, TASK_ID_MAX_LEN
from mailops.services.mailbox_catalog import MailboxCatalogError, list_unified_mailboxes
from mailops.services.pool import PoolServiceError, claim_random, complete_claim, release_claim
from mailops.services.provider_catalog import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    MAILBOX_SESSION_CLOSE_ENDPOINT,
    MAILBOX_SESSION_READ_ENDPOINT,
    MAILBOX_SESSION_START_ENDPOINT,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    TEMP_MAIL_PROVIDER_ENV,
    get_active_mailbox_provider_filter_contract,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_integration_manifest,
    get_external_mailbox_read_contract,
    get_mailbox_provider_catalog,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_mailbox_provider_health,
    get_mailbox_provider_preflight,
    get_mailbox_provider_readiness_summary,
    get_mailbox_provider_selection_policy,
    get_operator_temp_mail_default_provider,
    get_provider_alias_contract,
    get_provider_documentation_contract,
    get_provider_integration_guide,
    mailbox_session_provider_metadata,
    temp_mail_provider_config_status,
    temp_mail_provider_label,
)
from mailops.services.temp_mail_service import TempMailError, get_temp_mail_service

temp_mail_service = get_temp_mail_service()

MAILBOX_SESSION_STRATEGIES = {"pool_first", "task_temp_first", "pool_only", "task_temp_only"}

MAILBOX_SESSION_CLOSE_TYPES = {"pool_claim", "task_temp_mailbox"}

MAILBOX_SESSION_READ_ACTIONS = {
    "messages",
    "latest_message",
    "message_detail",
    "message_raw",
    "verification_code",
    "verification_link",
    "wait_message",
}
