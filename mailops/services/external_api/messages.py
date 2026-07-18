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

from .access import _get_proxy_url, get_current_external_api_consumer
from .constants import IMAP_SERVER_NEW, IMAP_SERVER_OLD
from .errors import InvalidParamError, MailNotFoundError, ProxyError, UpstreamReadFailedError
from .timefmt import _extract_email_address, _format_datetime, _parse_datetime, _utcnow

# Outlook IMAP 回退服务器（保持与内部接口一致）


def _build_message_summary(email_addr: str, item: Dict[str, Any], *, method: str) -> Dict[str, Any]:
    raw_from = item.get("from")
    if isinstance(raw_from, dict):
        from_address = (raw_from.get("emailAddress") or {}).get("address") or ""
    else:
        from_address = str(raw_from or item.get("from_address") or "")
    from_address = _extract_email_address(from_address)

    subject = str(item.get("subject") or "无主题")

    created_at_raw = (
        item.get("receivedDateTime") or item.get("date") or item.get("created_at") or item.get("received_at") or ""
    )
    created_dt = _parse_datetime(str(created_at_raw))
    created_at, timestamp = _format_datetime(created_dt, str(created_at_raw))

    content_preview = str(
        item.get("bodyPreview") or item.get("body_preview") or item.get("content_preview") or item.get("bodyPreview") or ""
    )

    is_read = bool(item.get("isRead") if "isRead" in item else item.get("is_read") or item.get("isRead") or False)

    return {
        "id": str(item.get("id") or ""),
        "email_address": email_addr,
        "from_address": from_address,
        "subject": subject,
        "content_preview": content_preview,
        "has_html": bool(item.get("has_html") or False),
        "timestamp": timestamp,
        "created_at": created_at,
        "is_read": is_read,
        "method": method,
    }


def list_messages_for_external(
    *,
    email_addr: str,
    folder: str = "inbox",
    skip: int = 0,
    top: int = 20,
) -> Tuple[List[Dict[str, Any]], str]:
    mailbox = mailbox_resolver.resolve_mailbox(email_addr)
    mailbox_meta = mailbox_resolver.ensure_mailbox_can_read(mailbox, consumer=get_current_external_api_consumer())
    folder = (folder or "inbox").strip().lower() or "inbox"
    skip = max(0, int(skip or 0))
    top = max(1, min(int(top or 20), 50))

    if mailbox.get("kind") == "temp":
        service = get_temp_mail_service()
        try:
            messages = service.list_messages(mailbox, sync_remote=True)
        except TempMailError as exc:
            raise UpstreamReadFailedError(
                "临时邮箱上游读取失败" if exc.code == "TEMP_EMAIL_UPSTREAM_READ_FAILED" else exc.message,
                data=exc.data,
            ) from exc
        sliced = messages[skip : skip + top]  # noqa: E203
        method_label = str(sliced[0].get("method") or "Temp Mail") if sliced else "Temp Mail"
        return sliced, method_label

    account = mailbox_meta

    account_type = (account.get("account_type") or "outlook").strip().lower()
    if account_type == "imap":
        result = get_emails_imap_generic(
            email_addr=email_addr,
            imap_password=account.get("imap_password", "") or "",
            imap_host=account.get("imap_host", "") or "",
            imap_port=account.get("imap_port", 993) or 993,
            folder=folder,
            provider=account.get("provider", "_default") or "_default",
            skip=skip,
            top=top,
        )
        if not result.get("success"):
            raise UpstreamReadFailedError("IMAP 读取失败", data=result.get("error"))
        method_label = str(result.get("method") or "IMAP (Generic)")
        emails = [_build_message_summary(email_addr, e, method=method_label) for e in (result.get("emails") or [])]
        return emails, method_label

    proxy_url = _get_proxy_url(account)

    graph_result = graph_service.get_emails_graph(
        account.get("client_id") or "",
        account.get("refresh_token") or "",
        folder=folder,
        skip=skip,
        top=top,
        proxy_url=proxy_url,
    )
    if graph_result.get("success"):
        method_label = "Graph API"
        emails = [_build_message_summary(email_addr, e, method=method_label) for e in (graph_result.get("emails") or [])]
        return emails, method_label

    graph_error = graph_result.get("error")
    if isinstance(graph_error, dict) and graph_error.get("type") in (
        "ProxyError",
        "ConnectionError",
    ):
        raise ProxyError("代理连接失败", data=graph_error)

    # Graph 失败 → IMAP(New) → IMAP(Old) 回退
    imap_new_result = imap_service.get_emails_imap_with_server(
        email_addr,
        account.get("client_id") or "",
        account.get("refresh_token") or "",
        folder,
        skip,
        top,
        IMAP_SERVER_NEW,
    )
    if imap_new_result.get("success"):
        method_label = "IMAP (New)"
        emails = [_build_message_summary(email_addr, e, method=method_label) for e in (imap_new_result.get("emails") or [])]
        return emails, method_label

    imap_old_result = imap_service.get_emails_imap_with_server(
        email_addr,
        account.get("client_id") or "",
        account.get("refresh_token") or "",
        folder,
        skip,
        top,
        IMAP_SERVER_OLD,
    )
    if imap_old_result.get("success"):
        method_label = "IMAP (Old)"
        emails = [_build_message_summary(email_addr, e, method=method_label) for e in (imap_old_result.get("emails") or [])]
        return emails, method_label

    raise UpstreamReadFailedError(
        "Graph/IMAP 均读取失败",
        data={
            "graph": graph_error,
            "imap_new": imap_new_result.get("error"),
            "imap_old": imap_old_result.get("error"),
        },
    )


def filter_messages(  # noqa: C901
    emails: List[Dict[str, Any]],
    *,
    from_contains: str = "",
    subject_contains: str = "",
    since_minutes: Optional[int] = None,
    baseline_timestamp: Optional[int] = None,
) -> List[Dict[str, Any]]:
    from_contains = (from_contains or "").strip().lower()
    subject_contains = (subject_contains or "").strip().lower()

    since_dt: Optional[datetime] = None
    if since_minutes is not None:
        try:
            since_minutes_int = int(since_minutes)
            if since_minutes_int > 0:
                since_dt = _utcnow() - timedelta(minutes=since_minutes_int)
        except Exception:
            since_dt = None

    filtered: List[Dict[str, Any]] = []
    for e in emails or []:
        from_addr = str(e.get("from_address") or e.get("from") or "").lower()
        subj = str(e.get("subject") or "").lower()
        if from_contains and from_contains not in from_addr:
            continue
        if subject_contains and subject_contains not in subj:
            continue

        if since_dt is not None:
            dt = _parse_datetime(e.get("created_at") or e.get("date") or e.get("receivedDateTime") or "")
            if dt and dt < since_dt:
                continue

        # PR#27: claim_token baseline 过滤——只保留 claimed_at 之后的邮件
        if baseline_timestamp is not None and baseline_timestamp > 0:
            if int(e.get("timestamp") or 0) < baseline_timestamp:
                continue

        filtered.append(e)
    return filtered


def get_latest_message_for_external(
    *,
    email_addr: str,
    folder: str = "inbox",
    from_contains: str = "",
    subject_contains: str = "",
    since_minutes: Optional[int] = None,
    baseline_timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    emails = list_messages_for_external(email_addr=email_addr, folder=folder, skip=0, top=20)[0]
    filtered = filter_messages(
        emails,
        from_contains=from_contains,
        subject_contains=subject_contains,
        since_minutes=since_minutes,
        baseline_timestamp=baseline_timestamp,
    )
    if not filtered:
        raise MailNotFoundError("未找到匹配邮件", data={"email": email_addr})
    # 保险起见按 timestamp 再排序一次（不同读取链路可能不严格有序）
    filtered.sort(key=lambda x: int(x.get("timestamp") or 0), reverse=True)
    return filtered[0]


def get_message_detail_for_external(  # noqa: C901
    *,
    email_addr: str,
    message_id: str,
    folder: str = "inbox",
) -> Dict[str, Any]:
    mailbox = mailbox_resolver.resolve_mailbox(email_addr)
    mailbox_meta = mailbox_resolver.ensure_mailbox_can_read(mailbox, consumer=get_current_external_api_consumer())
    message_id = (message_id or "").strip()
    if not message_id:
        raise InvalidParamError("message_id 不能为空")

    folder = (folder or "inbox").strip().lower() or "inbox"
    if mailbox.get("kind") == "temp":
        service = get_temp_mail_service()
        try:
            return service.refresh_message_detail(mailbox, message_id)
        except TempMailError as exc:
            if exc.code == "TEMP_EMAIL_MESSAGE_NOT_FOUND":
                raise MailNotFoundError(exc.message, data={"email": email_addr, "message_id": message_id}) from exc
            raise UpstreamReadFailedError(
                "临时邮箱上游读取失败" if exc.code == "TEMP_EMAIL_UPSTREAM_READ_FAILED" else exc.message,
                data=exc.data,
            ) from exc

    account = mailbox_meta
    account_type = (account.get("account_type") or "outlook").strip().lower()

    if account_type == "imap":
        detail_result = get_email_detail_imap_generic_result(
            email_addr=email_addr,
            imap_password=account.get("imap_password", "") or "",
            imap_host=account.get("imap_host", "") or "",
            imap_port=account.get("imap_port", 993) or 993,
            message_id=message_id,
            folder=folder,
            provider=account.get("provider", "_default") or "_default",
        )
        if not detail_result.get("success"):
            error_payload = detail_result.get("error") or {}
            raise UpstreamReadFailedError(str(error_payload.get("message") or "IMAP 读取失败"), data=error_payload)
        detail = detail_result.get("email") or {}

        html_content = str(detail.get("body_html") or "")
        content = str(detail.get("body_text") or "") or extract_email_text({"body_html": html_content})
        raw_content = str(detail.get("raw_content") or "")
        created_at_raw = str(detail.get("date") or "")
        created_at, timestamp = _format_datetime(_parse_datetime(created_at_raw), created_at_raw)
        return {
            "id": detail.get("id") or message_id,
            "email_address": email_addr,
            "from_address": _extract_email_address(detail.get("from") or ""),
            "to_address": detail.get("to") or "",
            "subject": detail.get("subject") or "",
            "content": content,
            "html_content": html_content,
            "raw_content": raw_content,
            "timestamp": timestamp,
            "created_at": created_at,
            "has_html": bool(html_content),
            "method": "IMAP (Generic)",
        }

    proxy_url = _get_proxy_url(account)

    detail = graph_service.get_email_detail_graph(
        account.get("client_id") or "",
        account.get("refresh_token") or "",
        message_id,
        proxy_url,
    )
    method_label = "Graph API"
    graph_raw_content = None
    if detail:
        graph_raw_content = graph_service.get_email_raw_graph(
            account.get("client_id") or "",
            account.get("refresh_token") or "",
            message_id,
            proxy_url,
        )
    if not detail:
        detail = imap_service.get_email_detail_imap_with_server(
            email_addr,
            account.get("client_id") or "",
            account.get("refresh_token") or "",
            message_id,
            folder,
            IMAP_SERVER_NEW,
        )
        method_label = "IMAP (New)"

    if not detail:
        detail = imap_service.get_email_detail_imap_with_server(
            email_addr,
            account.get("client_id") or "",
            account.get("refresh_token") or "",
            message_id,
            folder,
            IMAP_SERVER_OLD,
        )
        method_label = "IMAP (Old)"

    if not detail:
        raise MailNotFoundError("未找到邮件详情", data={"email": email_addr, "message_id": message_id})

    created_at_raw = ""
    timestamp = 0
    created_at = ""

    if "body" in detail and isinstance(detail.get("body"), dict):
        body_obj = detail.get("body") or {}
        body_type = str(body_obj.get("contentType") or "text").lower()
        body_content = str(body_obj.get("content") or "")

        html_content = body_content if body_type == "html" else ""
        content = body_content if body_type == "text" else extract_email_text({"body_html": html_content})
        raw_content = str(graph_raw_content or body_content)

        from_address = (detail.get("from") or {}).get("emailAddress", {}).get("address", "")
        to_address = ",".join([r.get("emailAddress", {}).get("address", "") for r in (detail.get("toRecipients") or [])])
        created_at_raw = str(detail.get("receivedDateTime") or "")
        subject = str(detail.get("subject") or "")
    else:
        # IMAP dict 格式
        content = str(detail.get("body") or "")
        html_content = ""
        raw_content = str(detail.get("raw_content") or content)
        from_address = _extract_email_address(str(detail.get("from") or ""))
        to_address = str(detail.get("to") or "")
        created_at_raw = str(detail.get("date") or "")
        subject = str(detail.get("subject") or "")

    created_at, timestamp = _format_datetime(_parse_datetime(created_at_raw), created_at_raw)

    return {
        "id": message_id,
        "email_address": email_addr,
        "from_address": _extract_email_address(from_address),
        "to_address": to_address,
        "subject": subject,
        "content": content,
        "html_content": html_content,
        "raw_content": raw_content,
        "timestamp": timestamp,
        "created_at": created_at,
        "has_html": bool(html_content),
        "method": method_label,
    }


def _extract_sender_address_from_message_item(item: Dict[str, Any]) -> str:
    raw_from = item.get("from")
    if isinstance(raw_from, dict):
        raw_from = (raw_from.get("emailAddress") or {}).get("address") or raw_from.get("address")
    return _extract_email_address(str(raw_from or item.get("from_address") or ""))


def _build_email_obj_from_detail(detail: Dict[str, Any], latest_summary: Dict[str, Any]) -> Dict[str, Any]:
    email_obj = {
        "subject": detail.get("subject") or latest_summary.get("subject") or "",
        "body_preview": latest_summary.get("content_preview") or "",
    }

    if "body" in detail and isinstance(detail.get("body"), dict):
        body_obj = detail.get("body") or {}
        body_type = str(body_obj.get("contentType") or "text").lower()
        body_content = str(body_obj.get("content") or "")
        email_obj["body"] = body_content if body_type == "text" else ""
        email_obj["body_html"] = body_content if body_type == "html" else ""
    else:
        email_obj["body"] = str(detail.get("body") or detail.get("content") or "")
        email_obj["body_html"] = str(detail.get("body_html") or detail.get("html_content") or "")

    return email_obj
