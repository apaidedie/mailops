from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from flask import current_app, jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.errors import build_error_payload, build_error_response
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import groups as groups_repo
from outlook_web.security.auth import api_key_required, login_required
from outlook_web.security.external_api_guard import external_api_guards
from outlook_web.services import account_compact_summary as compact_summary_service
from outlook_web.services import email_delete as email_delete_service
from outlook_web.services import external_api as external_api_service
from outlook_web.services import graph as graph_service
from outlook_web.services import imap as imap_service
from outlook_web.services import verification_channel_routing as verification_channel_service
from outlook_web.services.imap_generic import (
    get_email_detail_imap_generic_result,
    get_emails_imap_generic,
)
from outlook_web.services.mailbox_resolver import normalize_alias_email

_LOGGER = logging.getLogger("outlook_web.controllers.emails")

# IMAP 服务器配置

IMAP_SERVER_OLD = "outlook.office365.com"

IMAP_SERVER_NEW = "outlook.live.com"

_EXTERNAL_NESTED_UPSTREAM_CODES = {
    "IMAP_AUTH_FAILED",
    "IMAP_CONNECT_FAILED",
    "IMAP_FOLDER_NOT_FOUND",
}
