from __future__ import annotations

from typing import Any

from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import temp_emails as temp_emails_repo
from outlook_web.services import external_api as external_api_service
from outlook_web.services.temp_mail_service import TempMailError

_SECRET_MARKERS = (
    "password",
    "token",
    "secret",
    "credential",
    "consumer_key",
    "claim_token",
    "task_token",
    "jwt",
    "bearer",
    "api_key",
    "refresh_token",
)
_VALID_KINDS = {"account", "temp"}


class UnifiedMailboxMessageError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = int(status or 400)
        self.data = data or {}


def _normalize_kind(kind: Any) -> str:
    normalized = str(kind or "").strip().lower()
    if normalized not in _VALID_KINDS:
        raise UnifiedMailboxMessageError(
            "MAILBOX_KIND_INVALID",
            "邮箱类型无效",
            status=400,
            data={"kind": normalized, "allowed_kinds": sorted(_VALID_KINDS)},
        )
    return normalized


def _coerce_source_id(source_id: Any) -> int:
    try:
        value = int(source_id)
    except (TypeError, ValueError) as exc:
        raise UnifiedMailboxMessageError(
            "INVALID_PARAM", "source_id 参数无效", status=400
        ) from exc
    if value <= 0:
        raise UnifiedMailboxMessageError(
            "INVALID_PARAM", "source_id 参数无效", status=400
        )
    return value


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = default
    return min(max(normalized, minimum), maximum)


def _safe_string(value: Any) -> str:
    return str(value or "")


def _safe_source_id(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _public_mailbox_identity(mailbox: dict[str, Any]) -> dict[str, Any]:
    return _strip_secret_fields(
        {
            "kind": mailbox.get("kind"),
            "source_id": mailbox.get("source_id"),
            "email": mailbox.get("email"),
            "provider": mailbox.get("provider"),
            "provider_label": mailbox.get("provider_label") or mailbox.get("provider"),
            "read_capability": mailbox.get("read_capability"),
            "source": mailbox.get("source"),
        }
    )


def _mailbox_from_account(account: dict[str, Any]) -> dict[str, Any]:
    email = _safe_string(account.get("email")).strip()
    provider = (
        _safe_string(
            account.get("provider") or account.get("account_type") or "outlook"
        )
        .strip()
        .lower()
        or "outlook"
    )
    account_type = (
        _safe_string(account.get("account_type") or "outlook").strip().lower()
        or "outlook"
    )
    if provider == "cloudflare_temp_mail":
        from outlook_web.services import mailbox_resolver

        return {
            "kind": "account",
            "source_id": _safe_source_id(account.get("id")),
            "email": email,
            "provider": "cloudflare_temp_mail",
            "provider_label": "Cloudflare Temp Mail",
            "read_capability": "temp_provider",
            "source": "account_pool_temp",
            "mailbox": mailbox_resolver.resolve_mailbox(email),
        }
    return {
        "kind": "account",
        "source_id": _safe_source_id(account.get("id")),
        "email": email,
        "provider": provider,
        "provider_label": "Outlook" if account_type == "outlook" else provider,
        "read_capability": "imap" if account_type == "imap" else "graph",
        "source": "account",
    }


def _mailbox_from_temp(mailbox: dict[str, Any]) -> dict[str, Any]:
    record = mailbox.get("record") if isinstance(mailbox.get("record"), dict) else {}
    provider = (
        _safe_string(
            mailbox.get("provider_name") or mailbox.get("source") or "temp_mail"
        )
        .strip()
        .lower()
        or "temp_mail"
    )
    return {
        "kind": "temp",
        "source_id": _safe_source_id(record.get("id") or mailbox.get("id")),
        "email": _safe_string(mailbox.get("email")).strip(),
        "provider": provider,
        "provider_label": _safe_string(mailbox.get("provider_label") or provider),
        "read_capability": _safe_string(
            mailbox.get("read_capability") or "temp_provider"
        ),
        "source": _safe_string(mailbox.get("source") or provider),
        "mailbox": mailbox,
    }


def resolve_mailbox_identity(kind: Any, source_id: Any) -> dict[str, Any]:
    normalized_kind = _normalize_kind(kind)
    normalized_id = _coerce_source_id(source_id)
    if normalized_kind == "account":
        account = accounts_repo.get_account_by_id(normalized_id)
        if not account:
            raise UnifiedMailboxMessageError(
                "ACCOUNT_NOT_FOUND",
                "账号不存在",
                status=404,
                data={"source_id": normalized_id},
            )
        return _mailbox_from_account(account)

    mailbox = temp_emails_repo.get_temp_email_by_id(normalized_id, view="descriptor")
    if not mailbox:
        raise UnifiedMailboxMessageError(
            "TEMP_EMAIL_NOT_FOUND",
            "临时邮箱不存在",
            status=404,
            data={"source_id": normalized_id},
        )
    return _mailbox_from_temp(mailbox)


def _is_secret_key(key: str) -> bool:
    normalized = str(key or "").lower()
    return any(marker in normalized for marker in _SECRET_MARKERS)


def _strip_secret_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(k): _strip_secret_fields(v)
            for k, v in value.items()
            if not _is_secret_key(str(k))
        }
    if isinstance(value, list):
        return [_strip_secret_fields(item) for item in value]
    return value


def _normalize_message_summary(
    message: dict[str, Any], *, mailbox: dict[str, Any], folder: str, method: str
) -> dict[str, Any]:
    return {
        "id": _safe_string(message.get("id")),
        "email_address": mailbox["email"],
        "mailbox_id": f"{mailbox['kind']}:{mailbox['source_id']}",
        "kind": mailbox["kind"],
        "provider": mailbox["provider"],
        "provider_label": mailbox.get("provider_label") or mailbox["provider"],
        "folder": folder,
        "from_address": _safe_string(
            message.get("from_address") or message.get("from")
        ),
        "subject": _safe_string(message.get("subject") or "无主题"),
        "body_preview": _safe_string(
            message.get("body_preview") or message.get("content_preview")
        ),
        "created_at": _safe_string(message.get("created_at") or message.get("date")),
        "timestamp": _bounded_int(
            message.get("timestamp"), default=0, minimum=0, maximum=4102444800
        ),
        "has_html": bool(message.get("has_html")),
        "is_read": bool(message.get("is_read")),
        "method": _safe_string(message.get("method") or method),
    }


def _normalize_message_detail(
    detail: dict[str, Any], *, mailbox: dict[str, Any], folder: str
) -> dict[str, Any]:
    html_content = _safe_string(detail.get("html_content") or detail.get("body_html"))
    content = _safe_string(
        detail.get("content") or detail.get("body") or detail.get("body_text")
    )
    body_type = "html" if bool(detail.get("has_html") or html_content) else "text"
    return _strip_secret_fields(
        {
            "id": _safe_string(detail.get("id")),
            "email_address": mailbox["email"],
            "mailbox_id": f"{mailbox['kind']}:{mailbox['source_id']}",
            "kind": mailbox["kind"],
            "provider": mailbox["provider"],
            "provider_label": mailbox.get("provider_label") or mailbox["provider"],
            "folder": folder,
            "from_address": _safe_string(
                detail.get("from_address") or detail.get("from")
            ),
            "to_address": _safe_string(detail.get("to_address") or detail.get("to")),
            "subject": _safe_string(detail.get("subject") or "无主题"),
            "body": html_content if body_type == "html" else content,
            "body_text": content,
            "body_html": html_content,
            "body_type": body_type,
            "created_at": _safe_string(detail.get("created_at") or detail.get("date")),
            "timestamp": _bounded_int(
                detail.get("timestamp"), default=0, minimum=0, maximum=4102444800
            ),
            "has_html": body_type == "html",
            "method": _safe_string(detail.get("method") or ""),
        }
    )


def _map_external_error(
    exc: external_api_service.ExternalApiError,
) -> UnifiedMailboxMessageError:
    return UnifiedMailboxMessageError(
        str(exc.code or "INTERNAL_ERROR"),
        str(exc.message or "请求失败"),
        status=int(exc.status or 500),
        data=_strip_secret_fields(exc.data or {}),
    )


def _map_temp_mail_error(exc: TempMailError) -> UnifiedMailboxMessageError:
    return UnifiedMailboxMessageError(
        str(exc.code or "TEMP_EMAIL_UPSTREAM_READ_FAILED"),
        str(exc.message or "临时邮箱读取失败"),
        status=int(exc.status or 500),
        data=_strip_secret_fields(exc.data or {}),
    )


def _is_temp_provider_mailbox(mailbox: dict[str, Any]) -> bool:
    return str(mailbox.get("read_capability") or "").strip().lower() == "temp_provider"


def _read_temp_messages(
    mailbox: dict[str, Any], *, skip: int, top: int
) -> tuple[list[dict[str, Any]], str]:
    descriptor = (
        mailbox.get("mailbox") if isinstance(mailbox.get("mailbox"), dict) else None
    )
    target = descriptor or mailbox.get("email")
    from outlook_web.services.temp_mail_service import get_temp_mail_service

    service = get_temp_mail_service()
    try:
        messages = service.list_messages(target, sync_remote=True)
    except TempMailError as exc:
        if exc.code != "TEMP_EMAIL_UPSTREAM_READ_FAILED":
            raise
        messages = service.list_messages(target, sync_remote=False)
    sliced = messages[skip : skip + top]  # noqa: E203
    method = str(sliced[0].get("method") or "Temp Mail") if sliced else "Temp Mail"
    return sliced, method


def _read_temp_message_detail(
    mailbox: dict[str, Any], message_id: str
) -> dict[str, Any]:
    descriptor = (
        mailbox.get("mailbox") if isinstance(mailbox.get("mailbox"), dict) else None
    )
    target = descriptor or mailbox.get("email")
    from outlook_web.services.temp_mail_service import get_temp_mail_service

    service = get_temp_mail_service()
    try:
        return service.refresh_message_detail(target, message_id)
    except TempMailError as exc:
        if exc.code != "TEMP_EMAIL_UPSTREAM_READ_FAILED":
            raise
        return service.get_message_detail(target, message_id, refresh_if_missing=False)


def _read_temp_verification(
    mailbox: dict[str, Any],
    *,
    code_regex: str | None,
    code_length: str | None,
    code_source: str,
) -> dict[str, Any]:
    descriptor = (
        mailbox.get("mailbox") if isinstance(mailbox.get("mailbox"), dict) else None
    )
    target = descriptor or mailbox.get("email")
    from outlook_web.services.temp_mail_service import get_temp_mail_service

    service = get_temp_mail_service()
    return service.extract_verification(
        target,
        code_regex=code_regex,
        code_length=code_length,
        code_source=code_source,
    )


def list_unified_mailbox_messages(
    *,
    kind: Any,
    source_id: Any,
    folder: Any = "inbox",
    skip: Any = 0,
    top: Any = 20,
) -> dict[str, Any]:
    mailbox = resolve_mailbox_identity(kind, source_id)
    normalized_folder = _safe_string(folder or "inbox").strip().lower() or "inbox"
    normalized_skip = _bounded_int(skip, default=0, minimum=0, maximum=500)
    normalized_top = _bounded_int(top, default=20, minimum=1, maximum=50)
    try:
        if _is_temp_provider_mailbox(mailbox):
            messages, method = _read_temp_messages(
                mailbox, skip=normalized_skip, top=normalized_top
            )
        else:
            messages, method = external_api_service.list_messages_for_external(
                email_addr=mailbox["email"],
                folder=normalized_folder,
                skip=normalized_skip,
                top=normalized_top,
            )
    except external_api_service.ExternalApiError as exc:
        raise _map_external_error(exc) from exc
    except TempMailError as exc:
        raise _map_temp_mail_error(exc) from exc
    normalized = [
        _normalize_message_summary(
            message, mailbox=mailbox, folder=normalized_folder, method=method
        )
        for message in (messages or [])
        if _safe_string((message or {}).get("id"))
    ]
    return {
        "success": True,
        "mailbox": _public_mailbox_identity(mailbox),
        "messages": normalized,
        "count": len(normalized),
        "folder": normalized_folder,
        "method": method,
        "pagination": {
            "skip": normalized_skip,
            "top": normalized_top,
            "has_more": len(normalized) >= normalized_top,
        },
        "contract": {
            "version": 1,
            "message_id_field": "id",
            "detail_endpoint": "/api/mailboxes/{kind}/{source_id}/messages/{message_id}",
        },
    }


def get_unified_mailbox_message_detail(
    *,
    kind: Any,
    source_id: Any,
    message_id: Any,
    folder: Any = "inbox",
) -> dict[str, Any]:
    mailbox = resolve_mailbox_identity(kind, source_id)
    normalized_folder = _safe_string(folder or "inbox").strip().lower() or "inbox"
    normalized_message_id = _safe_string(message_id).strip()
    if not normalized_message_id:
        raise UnifiedMailboxMessageError(
            "INVALID_PARAM", "message_id 不能为空", status=400
        )
    try:
        if _is_temp_provider_mailbox(mailbox):
            detail = _read_temp_message_detail(mailbox, normalized_message_id)
        else:
            detail = external_api_service.get_message_detail_for_external(
                email_addr=mailbox["email"],
                message_id=normalized_message_id,
                folder=normalized_folder,
            )
    except external_api_service.ExternalApiError as exc:
        raise _map_external_error(exc) from exc
    except TempMailError as exc:
        raise _map_temp_mail_error(exc) from exc
    return {
        "success": True,
        "mailbox": _public_mailbox_identity(mailbox),
        "message": _normalize_message_detail(
            detail or {}, mailbox=mailbox, folder=normalized_folder
        ),
        "folder": normalized_folder,
        "contract": {"version": 1, "body_type_values": ["text", "html"]},
    }


def get_unified_mailbox_verification(
    *,
    kind: Any,
    source_id: Any,
    folder: Any = "inbox",
    code_regex: Any = None,
    code_length: Any = None,
    code_source: Any = "all",
) -> dict[str, Any]:
    mailbox = resolve_mailbox_identity(kind, source_id)
    normalized_folder = _safe_string(folder or "inbox").strip().lower() or "inbox"
    normalized_code_source = _safe_string(code_source or "all").strip().lower() or "all"
    try:
        if _is_temp_provider_mailbox(mailbox):
            result = _read_temp_verification(
                mailbox,
                code_regex=_safe_string(code_regex).strip() or None,
                code_length=_safe_string(code_length).strip() or None,
                code_source=normalized_code_source,
            )
        else:
            result = external_api_service.get_verification_result(
                email_addr=mailbox["email"],
                folder=normalized_folder,
                code_regex=_safe_string(code_regex).strip() or None,
                code_length=_safe_string(code_length).strip() or None,
                code_source=normalized_code_source,
                enable_channel_memory=False,
            )
    except external_api_service.ExternalApiError as exc:
        raise _map_external_error(exc) from exc
    except TempMailError as exc:
        raise _map_temp_mail_error(exc) from exc
    clean_result = _strip_secret_fields(result or {})
    return {
        "success": True,
        "mailbox": _public_mailbox_identity(mailbox),
        "verification": clean_result,
        "folder": normalized_folder,
        "contract": {
            "version": 1,
            "fields": [
                "verification_code",
                "verification_link",
                "formatted",
                "confidence",
            ],
        },
    }
