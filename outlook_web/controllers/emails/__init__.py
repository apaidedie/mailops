"""Package facade — re-exports public symbols for stable imports."""
from __future__ import annotations

import sys
import types

from outlook_web.repositories import accounts as accounts_repo
from outlook_web.services import graph as graph_service
from outlook_web.services import imap as imap_service
from outlook_web.services.imap_generic import get_emails_imap_generic

from .constants import (
    IMAP_SERVER_NEW,
    IMAP_SERVER_OLD,
    _EXTERNAL_NESTED_UPSTREAM_CODES,
    _LOGGER,
)
from .external_api import (
    api_external_get_latest_message,
    api_external_get_message_detail,
    api_external_get_message_raw,
    api_external_get_messages,
    api_external_get_probe_status,
    api_external_get_verification_code,
    api_external_get_verification_link,
    api_external_wait_message,
)
from .helpers import (
    _build_account_credential_decrypt_failed_response,
    _build_response_from_error_payload,
    _external_error_response,
    _parse_external_common_args,
    _persist_refresh_token,
    _resolve_external_error,
    _should_return_email_not_found_for_web_extract,
    _update_account_summary_from_verification,
)
from .mailbox_api import (
    api_batch_get_emails,
    api_delete_emails,
    api_extract_verification,
    api_get_email_detail,
    api_get_emails,
)
from . import constants, external_api, helpers, mailbox_api


class _EmailsModule(types.ModuleType):
    """Mirror attribute writes onto domain modules for monkeypatch tests."""

    def __getattr__(self, name: str):
        for module in (mailbox_api, helpers, external_api, constants):
            if hasattr(module, name):
                return getattr(module, name)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name: str, value):
        super().__setattr__(name, value)
        if name.startswith("__"):
            return
        for module in (mailbox_api, helpers, external_api, constants):
            if hasattr(module, name):
                setattr(module, name, value)


sys.modules[__name__].__class__ = _EmailsModule

__all__ = [
    "_LOGGER",
    "IMAP_SERVER_OLD",
    "IMAP_SERVER_NEW",
    "_EXTERNAL_NESTED_UPSTREAM_CODES",
    "accounts_repo",
    "graph_service",
    "imap_service",
    "get_emails_imap_generic",
    "_build_response_from_error_payload",
    "_build_account_credential_decrypt_failed_response",
    "_persist_refresh_token",
    "_update_account_summary_from_verification",
    "_parse_external_common_args",
    "_resolve_external_error",
    "_external_error_response",
    "_should_return_email_not_found_for_web_extract",
    "api_batch_get_emails",
    "api_get_emails",
    "api_delete_emails",
    "api_get_email_detail",
    "api_extract_verification",
    "api_external_get_messages",
    "api_external_get_latest_message",
    "api_external_get_message_detail",
    "api_external_get_message_raw",
    "api_external_get_verification_code",
    "api_external_get_verification_link",
    "api_external_wait_message",
    "api_external_get_probe_status",
]
