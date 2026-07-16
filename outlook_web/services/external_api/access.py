from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from outlook_web.audit import log_audit
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import external_api_keys as external_api_keys_repo
from outlook_web.repositories import groups as groups_repo
from outlook_web.security.auth import get_external_api_consumer
from outlook_web.services import graph as graph_service
from outlook_web.services import imap as imap_service
from outlook_web.services import (
    mailbox_resolver,
)
from outlook_web.services import verification_channel_routing as verification_channel_service
from outlook_web.services.imap_generic import (
    get_email_detail_imap_generic_result,
    get_emails_imap_generic,
)
from outlook_web.services.temp_mail_service import TempMailError, get_temp_mail_service
from outlook_web.services.verification_extract_log import (
    resolve_extract_log_outcome,
    write_verification_extract_log,
)
from outlook_web.services.verification_extractor import (
    apply_confidence_gate,
    enhance_verification_with_ai_fallback,
    extract_email_text,
    extract_verification_info_with_options,
    get_verification_ai_runtime_config,
    is_verification_ai_config_complete,
)

from .errors import AccountAccessForbiddenError, AccountNotFoundError, EmailScopeForbiddenError, InvalidParamError
from .timefmt import claimed_at_to_timestamp

# Outlook IMAP 回退服务器（保持与内部接口一致）


def _can_check_external_access() -> bool:
    try:
        from outlook_web.db import get_db

        get_db()
        return True
    except Exception:
        return False


def get_current_external_api_consumer() -> Dict[str, Any]:
    return get_external_api_consumer() or {}


def ensure_external_email_access(email_addr: str, *, allow_finished: bool = False) -> None:
    ensure_external_email_scope(email_addr, allow_finished=allow_finished)
    mailbox = mailbox_resolver.resolve_mailbox(email_addr)
    mailbox_resolver.ensure_mailbox_can_read(
        mailbox,
        consumer=get_current_external_api_consumer(),
        allow_finished=allow_finished,
    )


def ensure_external_email_scope(email_addr: str, *, allow_finished: bool = False) -> None:
    mailbox = mailbox_resolver.resolve_mailbox(email_addr)
    consumer = get_current_external_api_consumer()
    if mailbox.get("kind") == "account":
        allowed_emails = [str(item or "").strip().lower() for item in (consumer.get("allowed_emails") or [])]
        target_email = str(email_addr or "").strip().lower()
        if allowed_emails and target_email not in allowed_emails:
            raise EmailScopeForbiddenError(
                "当前 API Key 无权访问该邮箱",
                data={
                    "email": email_addr,
                    "consumer_id": consumer.get("id"),
                    "consumer_name": consumer.get("name"),
                },
            )
        return

    mailbox_resolver.ensure_mailbox_can_read(mailbox, consumer=consumer, allow_finished=allow_finished)


def _get_proxy_url(account: Dict[str, Any]) -> str:
    proxy_url = ""
    group_id = account.get("group_id")
    if not group_id:
        return ""
    group = groups_repo.get_group_by_id(group_id)
    if group:
        proxy_url = group.get("proxy_url", "") or ""
    return proxy_url


def require_account(email_addr: str) -> Dict[str, Any]:
    email_addr = (email_addr or "").strip()
    if not email_addr:
        raise InvalidParamError("email 参数不能为空")
    if "@" not in email_addr:
        raise InvalidParamError("email 参数无效")
    account = accounts_repo.get_account_by_email(email_addr)
    if not account:
        raise AccountNotFoundError("账号不存在", data={"email": email_addr})
    return account


def _preferred_probe_method(account: Dict[str, Any]) -> str:
    account_type = (account.get("account_type") or "outlook").strip().lower()
    return "imap_generic" if account_type == "imap" else "graph"


def _account_can_read(account: Dict[str, Any]) -> bool:
    status = (account.get("status") or "active").strip().lower()
    if status != "active":
        return False
    account_type = (account.get("account_type") or "outlook").strip().lower()
    if account_type == "imap":
        return bool((account.get("imap_host") or "").strip()) and bool((account.get("imap_password") or "").strip())
    return bool((account.get("client_id") or "").strip()) and bool((account.get("refresh_token") or "").strip())


def can_account_read(account: Dict[str, Any]) -> bool:
    return _account_can_read(account)


def ensure_account_can_read(account: Dict[str, Any]) -> Dict[str, Any]:
    if _account_can_read(account):
        return account
    raise AccountAccessForbiddenError(
        "当前账号不可读取",
        data={
            "email": account.get("email") or "",
            "status": account.get("status") or "",
            "account_type": account.get("account_type") or "",
        },
    )


def resolve_external_mail_scope(
    email_addr: Optional[str],
    claim_token: Optional[str],
    *,
    allow_finished: bool = False,
) -> tuple[str, Optional[int]]:
    """
    根据 email_addr 或 claim_token 确定目标邮箱地址和 baseline_timestamp。

    返回 (email_addr, baseline_timestamp) 元组。
    - 若提供 claim_token，从领取上下文获取 email 和 claimed_at 时间戳。
    - claim_token 与 email_addr 若同时存在，claim_token 优先。
    - claimed_at 作为邮件读取的 baseline（避免读到领取之前的旧邮件）。
    """
    from outlook_web.services.pool import get_claim_context

    baseline: Optional[int] = None

    if claim_token and claim_token.strip():
        ctx = get_claim_context(claim_token=claim_token.strip())
        if ctx is None:
            raise InvalidParamError("claim_token 无效或已过期", data={"claim_token": claim_token})
        resolved_email = ctx.get("email") or ""
        if not resolved_email:
            raise InvalidParamError("claim_token 对应账号无邮箱地址")
        # 若 email_addr 也有值，校验一致性
        if email_addr and email_addr.strip() and email_addr.strip().lower() != resolved_email.lower():
            raise InvalidParamError(
                "claim_token 与 email 不一致",
                data={"email": email_addr, "claim_token_email": resolved_email},
            )
        email_addr = resolved_email
        baseline = claimed_at_to_timestamp(ctx.get("claimed_at") or "")

    if not email_addr or "@" not in (email_addr or ""):
        raise InvalidParamError("email 参数无效")

    ensure_external_email_access(email_addr, allow_finished=allow_finished)
    return email_addr, baseline


def record_claim_read_context(
    *,
    claim_token: Optional[str],
    email_addr: str,
    caller_id: Optional[str] = None,
    task_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """
    当通过 claim_token 读取邮件时，记录一条 read 日志（用于审计和 debug）。
    若无 claim_token 则静默跳过。
    """
    if not claim_token or not claim_token.strip():
        return
    try:
        from outlook_web.services.pool import (
            append_claim_read_context,
            get_claim_context,
        )

        ctx = get_claim_context(claim_token=claim_token.strip())
        if ctx is None:
            return
        consumer = get_current_external_api_consumer() or {}
        resolved_caller_id = str(caller_id or consumer.get("consumer_key") or consumer.get("name") or "")
        resolved_task_id = str(task_id or "")
        append_claim_read_context(
            account_id=ctx["account_id"],
            claim_token=claim_token.strip(),
            caller_id=resolved_caller_id,
            task_id=resolved_task_id,
            detail=detail or f"read via external API, email={email_addr}",
        )
    except Exception:
        pass


def audit_external_api_access(
    *,
    action: str,
    email_addr: str,
    endpoint: str,
    status: str,
    details: Dict[str, Any] | None = None,
):
    safe_details: Dict[str, Any] = {"endpoint": endpoint, "status": status}
    consumer = get_current_external_api_consumer()
    if consumer:
        safe_details.update(
            {
                "consumer_id": consumer.get("id"),
                "consumer_key": consumer.get("consumer_key"),
                "consumer_name": consumer.get("name"),
                "consumer_source": consumer.get("source"),
            }
        )
        if consumer.get("allowed_emails"):
            safe_details["consumer_allowed_emails"] = consumer.get("allowed_emails")
    if details:
        # 避免日志中输出敏感信息（如 API Key）
        safe_details.update(details)

    try:
        details_text = json.dumps(safe_details, ensure_ascii=False)
    except Exception:
        details_text = str(safe_details)

    log_audit(action, "external_api", email_addr, details_text)
    try:
        if consumer:
            external_api_keys_repo.record_external_api_consumer_usage(
                consumer_key=str(consumer.get("consumer_key") or ""),
                consumer_name=str(consumer.get("name") or ""),
                endpoint=endpoint,
                status=status,
            )
    except Exception:
        pass
