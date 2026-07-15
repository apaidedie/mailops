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

from .access import _get_proxy_url, ensure_external_email_access
from .errors import ExternalApiError, InvalidParamError, MailNotFoundError, UpstreamReadFailedError, VerificationAiConfigIncompleteError, VerificationCodeNotFoundError, VerificationLinkNotFoundError
from .messages import get_latest_message_for_external, get_message_detail_for_external

# Outlook IMAP 回退服务器（保持与内部接口一致）

def _shape_verification_result_by_expected_field(extracted: Dict[str, Any], expected_field: str | None) -> Dict[str, Any]:
    """按接口语义裁剪输出：code 接口只返回 code，link 接口只返回 link。"""
    if expected_field not in {"verification_code", "verification_link"}:
        return extracted

    result = dict(extracted or {})
    if expected_field == "verification_code":
        result["verification_link"] = None
        result["link_confidence"] = "low"
    else:
        result["verification_code"] = None
        result["code_confidence"] = "low"

    parts = [v for v in (result.get("verification_code"), result.get("verification_link")) if v]
    result["formatted"] = " ".join(parts) if parts else None
    result["confidence"] = (
        "high" if result.get("code_confidence") == "high" or result.get("link_confidence") == "high" else "low"
    )
    return result

def _classify_extract_error(exc: Exception) -> str:
    # 将异常分类为日志可读的 error_code：业务异常用语义 code，未知异常用类名大写
    if isinstance(exc, ExternalApiError):
        return str(exc.code or "INTERNAL_ERROR")
    return type(exc).__name__.upper()

def _resolve_extract_log_channel(result: Optional[Dict[str, Any]], *, folder: str, method: str) -> str:
    # 确定日志渠道标签：优先使用渠道路由内置标记，回退到 method/folder 推断
    if result and result.get("_log_channel"):
        return str(result.get("_log_channel") or "")

    mapped = verification_channel_service.map_method_to_verification_channel(method, folder=folder)
    if mapped:
        return mapped

    method_text = str(method or "").strip().lower()
    if "temp" in method_text:
        return "temp_mail"
    return "unknown"

def _strip_extract_log_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    # 移除日志埋点专用的内部字段，避免泄露给 API 调用方
    clean = dict(result or {})
    clean.pop("_log_channel", None)
    clean.pop("_log_used_ai", None)
    return clean

def _get_db_for_log():
    from outlook_web.db import get_db

    return get_db()

def _write_extract_log(
    *,
    account_id: Optional[int],
    channel: str,
    started_at: float,
    finished_at: float,
    result_type: str,
    code_found: Optional[str],
    used_ai: bool,
    error_code: Optional[str],
    trace_id: Optional[str],
) -> None:
    # 二次异常隔离：write_verification_extract_log 内部已静默，这里再加一层防止 get_db() 抛出
    try:
        db = _get_db_for_log()
        write_verification_extract_log(
            account_id=account_id,
            channel=channel,
            started_at=started_at,
            finished_at=finished_at,
            result_type=result_type,
            code_found=code_found,
            used_ai=used_ai,
            error_code=error_code,
            trace_id=trace_id,
            db=db,
        )
    except Exception:
        pass

def _extract_verification_with_memory_for_outlook(  # noqa: C901
    *,
    account: Dict[str, Any],
    email_addr: str,
    from_contains: str,
    subject_contains: str,
    since_minutes: Optional[int],
    baseline_timestamp: Optional[int],
    resolved_policy: Dict[str, Any],
    code_source: str,
    expected_field: str | None = None,
) -> Dict[str, Any]:
    ensure_external_email_access(email_addr)
    result = verification_channel_service.extract_verification_for_outlook(
        account=account,
        proxy_url=_get_proxy_url(account),
        resolved_policy=resolved_policy,
        code_source=code_source,
        expected_field=expected_field,
        from_contains=from_contains,
        subject_contains=subject_contains,
        since_minutes=since_minutes,
        baseline_timestamp=baseline_timestamp,
    )

    if not result.get("success"):
        error_code = str(result.get("error_code") or "UNKNOWN")
        if error_code == "ACCOUNT_AUTH_EXPIRED":
            raise UpstreamReadFailedError("Graph/IMAP 均读取失败", data=result.get("upstream_errors"))
        if error_code == "VERIFICATION_NOT_FOUND":
            if expected_field == "verification_code":
                raise VerificationCodeNotFoundError(
                    "未找到符合条件的验证码邮件",
                    data={
                        "email": email_addr,
                        "upstream_errors": result.get("upstream_errors"),
                    },
                )
            if expected_field == "verification_link":
                raise VerificationLinkNotFoundError(
                    "未找到符合条件的验证链接邮件",
                    data={
                        "email": email_addr,
                        "upstream_errors": result.get("upstream_errors"),
                    },
                )
        raise MailNotFoundError(
            "未找到匹配邮件",
            data={
                "email": email_addr,
                "upstream_errors": result.get("upstream_errors"),
            },
        )

    if result.get("new_refresh_token"):
        try:
            new_token = str(result.get("new_refresh_token") or "").strip()
            if new_token and accounts_repo.update_refresh_token_if_changed(int(account["id"]), new_token):
                account["refresh_token"] = new_token
        except Exception:
            pass

    shaped = _shape_verification_result_by_expected_field(result.get("data") or {}, expected_field)
    shaped["_log_channel"] = (
        result.get("_log_channel") or (result.get("data") or {}).get("_log_channel") or result.get("channel_used") or "unknown"
    )
    shaped["_log_used_ai"] = bool(
        result.get("_log_used_ai")
        or (result.get("data") or {}).get("_used_ai")
        or (result.get("data") or {}).get("_log_used_ai")
    )
    return shaped

def _resolve_verification_extract_context(
    email_addr: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[Dict[str, Any]]]:
    account = accounts_repo.get_account_by_email((email_addr or "").strip())
    account_id: Optional[int] = None
    if account and account.get("id") is not None:
        try:
            account_id = int(account.get("id"))
        except (TypeError, ValueError):
            account_id = None

    group = None
    if account and account.get("group_id"):
        try:
            group_id = int(account.get("group_id"))
        except (TypeError, ValueError):
            group_id = 0
        if group_id > 0:
            group = groups_repo.get_group_by_id(group_id)
    return account, account_id, group

def _resolve_verification_policy_for_request(
    *,
    code_length: str | None,
    code_regex: str | None,
    group: Optional[Dict[str, Any]],
    apply_default_code_length: bool,
) -> Dict[str, Any]:
    try:
        return groups_repo.resolve_group_verification_policy(
            request_code_length=code_length,
            request_code_regex=code_regex,
            group=group,
            default_code_length="6-6",
            apply_default=apply_default_code_length,
            request_error_code="INVALID_PARAM",
        )
    except groups_repo.GroupPolicyValidationError as exc:
        raise InvalidParamError("参数错误") from exc

def _ensure_verification_ai_ready() -> None:
    ai_config = get_verification_ai_runtime_config()
    if ai_config.get("enabled") and not is_verification_ai_config_complete(ai_config):
        raise VerificationAiConfigIncompleteError("验证码 AI 已开启，请完整填写 Base URL、API Key、模型 ID")

def _should_use_outlook_memory_extract(
    *,
    account: Optional[Dict[str, Any]],
    folder: str,
    enable_channel_memory: bool,
) -> bool:
    if not account or not enable_channel_memory:
        return False
    if str(folder or "inbox").strip().lower() != "inbox":
        return False
    return verification_channel_service.is_outlook_oauth_account(account)

def _finalize_verification_extract_log(
    *,
    account_id: Optional[int],
    channel: str,
    started_at: float,
    result: Optional[Dict[str, Any]],
    used_ai: bool,
    error_code: Optional[str],
    trace_id: Optional[str],
) -> None:
    result_type, code_found = resolve_extract_log_outcome(result)
    _write_extract_log(
        account_id=account_id,
        channel=channel,
        started_at=started_at,
        finished_at=time.time(),
        result_type=result_type,
        code_found=code_found,
        used_ai=used_ai,
        error_code=error_code,
        trace_id=trace_id,
    )

def _run_logged_verification_extract(
    *,
    account_id: Optional[int],
    started_at: float,
    trace_id: Optional[str],
    extract_fn: Callable[[], Tuple[Dict[str, Any], str, bool]],
) -> Dict[str, Any]:
    result: Optional[Dict[str, Any]] = None
    log_channel = "unknown"
    used_ai = False
    error_code: Optional[str] = None

    try:
        result, log_channel, used_ai = extract_fn()
        return _strip_extract_log_fields(result)
    except Exception as exc:
        error_code = _classify_extract_error(exc)
        raise
    finally:
        _finalize_verification_extract_log(
            account_id=account_id,
            channel=log_channel,
            started_at=started_at,
            result=result,
            used_ai=used_ai,
            error_code=error_code,
            trace_id=trace_id,
        )

def _run_outlook_memory_verification_extract(
    *,
    account: Dict[str, Any],
    email_addr: str,
    from_contains: str,
    subject_contains: str,
    since_minutes: Optional[int],
    baseline_timestamp: Optional[int],
    resolved_policy: Dict[str, Any],
    code_source: str,
    expected_field: str | None,
) -> Tuple[Dict[str, Any], str, bool]:
    result = _extract_verification_with_memory_for_outlook(
        account=account,
        email_addr=email_addr,
        from_contains=from_contains,
        subject_contains=subject_contains,
        since_minutes=since_minutes,
        baseline_timestamp=baseline_timestamp,
        resolved_policy=resolved_policy,
        code_source=code_source,
        expected_field=expected_field,
    )
    return result, str(result.get("_log_channel") or "unknown"), bool(result.get("_log_used_ai"))

def _run_generic_verification_extract(
    *,
    email_addr: str,
    folder: str,
    from_contains: str,
    subject_contains: str,
    since_minutes: Optional[int],
    baseline_timestamp: Optional[int],
    resolved_policy: Dict[str, Any],
    code_source: str,
    expected_field: str | None,
) -> Tuple[Dict[str, Any], str, bool]:
    latest_summary = get_latest_message_for_external(
        email_addr=email_addr,
        folder=folder,
        from_contains=from_contains,
        subject_contains=subject_contains,
        since_minutes=since_minutes,
        baseline_timestamp=baseline_timestamp,
    )
    message_id = str(latest_summary.get("id") or "")
    method = str(latest_summary.get("method") or "")

    detail = get_message_detail_for_external(email_addr=email_addr, message_id=message_id, folder=folder)

    email_obj = {
        "subject": detail.get("subject") or "",
        "body": detail.get("content") or "",
        "body_html": detail.get("html_content") or "",
        "body_preview": latest_summary.get("content_preview") or "",
    }
    extracted = extract_verification_info_with_options(
        email_obj,
        code_regex=resolved_policy.get("code_regex"),
        code_length=resolved_policy.get("code_length"),
        code_source=code_source,
        enforce_mutual_exclusion=False,
    )
    extracted = enhance_verification_with_ai_fallback(
        email=email_obj,
        extracted=extracted,
        code_regex=resolved_policy.get("code_regex"),
        code_length=resolved_policy.get("code_length"),
        code_source=code_source,
        enforce_mutual_exclusion=False,
    )
    extracted = apply_confidence_gate(extracted, enforce_mutual_exclusion=False)

    extracted["email"] = email_addr
    extracted["matched_email_id"] = message_id
    extracted["from"] = detail.get("from_address") or latest_summary.get("from_address") or ""
    extracted["subject"] = detail.get("subject") or latest_summary.get("subject") or ""
    extracted["received_at"] = detail.get("created_at") or latest_summary.get("created_at") or ""
    extracted["method"] = detail.get("method") or method
    extracted["_log_channel"] = (
        "ai_fallback"
        if extracted.get("_used_ai") and (extracted.get("verification_code") or extracted.get("verification_link"))
        else _resolve_extract_log_channel(extracted, folder=folder, method=method)
    )
    extracted["_log_used_ai"] = bool(extracted.get("_used_ai"))

    result = _shape_verification_result_by_expected_field(extracted, expected_field)
    return result, _resolve_extract_log_channel(result, folder=folder, method=method), bool(result.get("_log_used_ai"))

def get_verification_result(
    *,
    email_addr: str,
    folder: str = "inbox",
    from_contains: str = "",
    subject_contains: str = "",
    since_minutes: Optional[int] = None,
    code_regex: str | None = None,
    code_length: str | None = None,
    code_source: str = "all",
    baseline_timestamp: Optional[int] = None,
    apply_default_code_length: bool = True,
    expected_field: str | None = None,
    enable_channel_memory: bool = True,
) -> Dict[str, Any]:
    started_at = time.time()
    trace_id = None
    account, account_id, group = _resolve_verification_extract_context(email_addr)
    resolved_policy = _resolve_verification_policy_for_request(
        code_length=code_length,
        code_regex=code_regex,
        group=group,
        apply_default_code_length=apply_default_code_length,
    )
    _ensure_verification_ai_ready()

    if _should_use_outlook_memory_extract(
        account=account,
        folder=folder,
        enable_channel_memory=enable_channel_memory,
    ):
        assert account is not None
        return _run_logged_verification_extract(
            account_id=account_id,
            started_at=started_at,
            trace_id=trace_id,
            extract_fn=lambda: _run_outlook_memory_verification_extract(
                account=account,
                email_addr=email_addr,
                from_contains=from_contains,
                subject_contains=subject_contains,
                since_minutes=since_minutes,
                baseline_timestamp=baseline_timestamp,
                resolved_policy=resolved_policy,
                code_source=code_source,
                expected_field=expected_field,
            ),
        )

    return _run_logged_verification_extract(
        account_id=account_id,
        started_at=started_at,
        trace_id=trace_id,
        extract_fn=lambda: _run_generic_verification_extract(
            email_addr=email_addr,
            folder=folder,
            from_contains=from_contains,
            subject_contains=subject_contains,
            since_minutes=since_minutes,
            baseline_timestamp=baseline_timestamp,
            resolved_policy=resolved_policy,
            code_source=code_source,
            expected_field=expected_field,
        ),
    )
