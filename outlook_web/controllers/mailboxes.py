from __future__ import annotations

from typing import Any

from flask import jsonify, request

from outlook_web.errors import build_error_response
from outlook_web.security.auth import login_required
from outlook_web.services.mailbox_catalog import (
    MailboxCatalogError,
    list_unified_mailboxes,
)
from outlook_web.services.unified_mailbox_messages import (
    UnifiedMailboxMessageError,
    get_unified_mailbox_message_detail,
    get_unified_mailbox_verification,
    list_unified_mailbox_messages,
)


@login_required
def api_list_mailboxes() -> Any:
    try:
        payload = list_unified_mailboxes(
            kind=request.args.get("kind", "all"),
            status=request.args.get("status", "all"),
            read_capability=request.args.get("read_capability", "all"),
            action=request.args.get("action", "all"),
            provider=request.args.get("provider", "all"),
            search=request.args.get("search", ""),
            sort=request.args.get("sort", "updated_desc"),
            page=request.args.get("page", 1),
            page_size=request.args.get("page_size", 50),
        )
        return jsonify(payload)
    except MailboxCatalogError as exc:
        return build_error_response(
            exc.code,
            exc.message,
            message_en="Mailbox catalog filter is invalid",
            status=400,
            extra=exc.data,
        )


def _unified_message_error_response(exc: UnifiedMailboxMessageError) -> Any:
    return build_error_response(
        exc.code,
        exc.message,
        message_en="Unified mailbox message operation failed",
        status=exc.status,
        extra=exc.data,
    )


@login_required
def api_list_mailbox_messages(kind: str, source_id: int) -> Any:
    try:
        payload = list_unified_mailbox_messages(
            kind=kind,
            source_id=source_id,
            folder=request.args.get("folder", "inbox"),
            skip=request.args.get("skip", 0),
            top=request.args.get("top", 20),
        )
        return jsonify(payload)
    except UnifiedMailboxMessageError as exc:
        return _unified_message_error_response(exc)


@login_required
def api_get_mailbox_message_detail(kind: str, source_id: int, message_id: str) -> Any:
    try:
        payload = get_unified_mailbox_message_detail(
            kind=kind,
            source_id=source_id,
            message_id=message_id,
            folder=request.args.get("folder", "inbox"),
        )
        return jsonify(payload)
    except UnifiedMailboxMessageError as exc:
        return _unified_message_error_response(exc)


@login_required
def api_get_mailbox_verification(kind: str, source_id: int) -> Any:
    try:
        payload = get_unified_mailbox_verification(
            kind=kind,
            source_id=source_id,
            folder=request.args.get("folder", "inbox"),
            code_regex=request.args.get("code_regex"),
            code_length=request.args.get("code_length"),
            code_source=request.args.get("code_source", "all"),
        )
        return jsonify(payload)
    except UnifiedMailboxMessageError as exc:
        return _unified_message_error_response(exc)
