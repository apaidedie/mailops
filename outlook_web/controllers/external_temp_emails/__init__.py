"""Package facade — re-exports public symbols for stable imports."""

from __future__ import annotations

# Historical unittest.patch target: controllers.external_temp_emails.external_api_service.*
from outlook_web.services import external_api as external_api_service

from .constants import (
    MAILBOX_SESSION_CLOSE_TYPES,
    MAILBOX_SESSION_READ_ACTIONS,
    MAILBOX_SESSION_STRATEGIES,
    temp_mail_service,
)
from .helpers import (
    _account_id_from_body,
    _audit,
    _close_pool_session,
    _close_task_temp_session,
    _consumer_can_use_pool,
    _external_error_response,
    _feature_disabled_response,
    _forbidden,
    _int_body_field,
    _json_object_body,
    _optional_since_minutes,
    _pool_close_disabled_response,
    _pool_disabled_response,
    _pool_error_code,
    _pool_session_payload,
    _read_messages_result,
    _read_session_action,
    _resolve_session_read_target,
    _session_read_params,
    _session_read_payload,
    _start_pool_session,
    _start_task_temp_session,
    _strategy_uses_pool,
    _task_temp_session_payload,
    _validate_required_workflow_fields,
)
from .lifecycle_api import (
    api_external_apply_temp_email,
    api_external_finish_temp_email,
)
from .providers_api import (
    api_external_get_provider_health,
    api_external_get_provider_preflight,
    api_external_get_providers,
    api_external_list_mailboxes,
)
from .session_api import (
    api_external_close_mailbox_session,
    api_external_read_mailbox_session,
    api_external_start_mailbox_session,
)

__all__ = [
    "external_api_service",
    "temp_mail_service",
    "MAILBOX_SESSION_STRATEGIES",
    "MAILBOX_SESSION_CLOSE_TYPES",
    "MAILBOX_SESSION_READ_ACTIONS",
    "_audit",
    "_forbidden",
    "_json_object_body",
    "_validate_required_workflow_fields",
    "_pool_error_code",
    "_consumer_can_use_pool",
    "_strategy_uses_pool",
    "_pool_disabled_response",
    "_feature_disabled_response",
    "_pool_close_disabled_response",
    "_account_id_from_body",
    "_pool_session_payload",
    "_task_temp_session_payload",
    "_int_body_field",
    "_optional_since_minutes",
    "_session_read_params",
    "_resolve_session_read_target",
    "_session_read_payload",
    "_read_messages_result",
    "_read_session_action",
    "_external_error_response",
    "_start_pool_session",
    "_start_task_temp_session",
    "_close_pool_session",
    "_close_task_temp_session",
    "api_external_list_mailboxes",
    "api_external_get_providers",
    "api_external_get_provider_preflight",
    "api_external_get_provider_health",
    "api_external_start_mailbox_session",
    "api_external_read_mailbox_session",
    "api_external_close_mailbox_session",
    "api_external_apply_temp_email",
    "api_external_finish_temp_email",
]
