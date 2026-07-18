from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from mailops.audit import log_audit
from mailops.repositories import accounts as accounts_repo
from mailops.repositories import external_api_keys as external_api_keys_repo
from mailops.repositories import groups as groups_repo
from mailops.security.auth import get_external_api_consumer
from mailops.services import graph as graph_service
from mailops.services import imap as imap_service
from mailops.services import (
    mailbox_resolver,
)
from mailops.services import verification_channel_routing as verification_channel_service
from mailops.services.imap_generic import (
    get_email_detail_imap_generic_result,
    get_emails_imap_generic,
)
from mailops.services.temp_mail_service import TempMailError, get_temp_mail_service
from mailops.services.verification_extract_log import (
    resolve_extract_log_outcome,
    write_verification_extract_log,
)
from mailops.services.verification_extractor import (
    apply_confidence_gate,
    enhance_verification_with_ai_fallback,
    extract_email_text,
    extract_verification_info_with_options,
    get_verification_ai_runtime_config,
    is_verification_ai_config_complete,
)

# Outlook IMAP 回退服务器（保持与内部接口一致）


class ExternalApiError(Exception):
    code = "INTERNAL_ERROR"
    status = 500

    def __init__(self, message: str, *, data: Any = None):
        super().__init__(message)
        self.message = message
        self.data = data


class InvalidParamError(ExternalApiError):
    code = "INVALID_PARAM"
    status = 400


class AccountNotFoundError(ExternalApiError):
    code = "ACCOUNT_NOT_FOUND"
    status = 404


class MailNotFoundError(ExternalApiError):
    code = "MAIL_NOT_FOUND"
    status = 404


class VerificationCodeNotFoundError(ExternalApiError):
    code = "VERIFICATION_CODE_NOT_FOUND"
    status = 404


class VerificationLinkNotFoundError(ExternalApiError):
    code = "VERIFICATION_LINK_NOT_FOUND"
    status = 404


class ProxyError(ExternalApiError):
    code = "PROXY_ERROR"
    status = 502


class UpstreamReadFailedError(ExternalApiError):
    code = "UPSTREAM_READ_FAILED"
    status = 502


class EmailScopeForbiddenError(ExternalApiError):
    code = "EMAIL_SCOPE_FORBIDDEN"
    status = 403


class AccountAccessForbiddenError(ExternalApiError):
    code = "ACCOUNT_ACCESS_FORBIDDEN"
    status = 403


class TaskFinishedError(ExternalApiError):
    code = "TASK_FINISHED"
    status = 409


class TaskTokenInvalidError(ExternalApiError):
    code = "TASK_TOKEN_INVALID"
    status = 404


class FeatureDisabledError(ExternalApiError):
    code = "FEATURE_DISABLED"
    status = 403


class ProbeCancelledError(ExternalApiError):
    code = "PROBE_CANCELLED"
    status = 409


class MailboxConflictError(ExternalApiError):
    code = "MAILBOX_CONFLICT"
    status = 409


class VerificationAiConfigIncompleteError(ExternalApiError):
    code = "VERIFICATION_AI_CONFIG_INCOMPLETE"
    status = 400


def ok(data: Any = None, *, message: str = "success") -> Dict[str, Any]:
    return {"success": True, "code": "OK", "message": message, "data": data}


def fail(code: str, message: str, *, data: Any = None) -> Dict[str, Any]:
    return {"success": False, "code": code, "message": message, "data": data}
