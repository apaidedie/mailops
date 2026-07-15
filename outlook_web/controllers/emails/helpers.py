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

from .constants import _EXTERNAL_NESTED_UPSTREAM_CODES

def _build_response_from_error_payload(error_payload: dict[str, Any]):
    return build_error_response(
        str(error_payload.get("code") or "INTERNAL_ERROR"),
        str(error_payload.get("message") or "请求失败"),
        message_en=str(error_payload.get("message_en") or "Request failed"),
        err_type=str(error_payload.get("type") or "Error"),
        status=int(error_payload.get("status") or 500),
        details=error_payload.get("details") or "",
        trace_id=error_payload.get("trace_id"),
    )

def _build_account_credential_decrypt_failed_response(account: dict[str, Any]):
    credential_errors = account.get("_credential_errors") or []
    if not credential_errors:
        return None

    fields = sorted({str(item.get("field") or "").strip() for item in credential_errors if item.get("field")})
    details = {
        "fields": fields,
        "errors": credential_errors,
    }
    return build_error_response(
        "ACCOUNT_CREDENTIAL_DECRYPT_FAILED",
        "账号凭据解密失败，请重新保存该账号后重试",
        message_en="Account credentials could not be decrypted. Re-save the account and try again.",
        err_type="CredentialDecryptError",
        status=500,
        details=credential_errors,
        extra={"details": details},
    )

def _persist_refresh_token(account: Dict[str, Any], new_refresh_token: str) -> None:
    token = str(new_refresh_token or "").strip()
    if not token:
        return
    if accounts_repo.update_refresh_token_if_changed(int(account["id"]), token):
        account["refresh_token"] = token

def _update_account_summary_from_verification(account: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    return compact_summary_service.update_summary_from_verification(
        int(account["id"]),
        message={
            "id": data.get("matched_email_id") or "",
            "subject": data.get("subject") or "",
            "from": data.get("from") or "",
            "date": data.get("received_at") or "",
            "receivedDateTime": data.get("received_at") or "",
            "folder": data.get("folder") or "inbox",
        },
        verification_code=str(data.get("verification_code") or ""),
        folder=str(data.get("folder") or "inbox"),
    )


# ==================== 邮件 API ====================

def _parse_external_common_args(*, default_since_minutes: int | None = None) -> dict:
    """解析 external API 通用 query 参数（按 TDD-00008 做基础校验）。

    PR#27 新增：支持 claim_token 参数。若提供 claim_token，则从领取上下文中
    推断 email 和 baseline_timestamp，并优先使用（覆盖 email 参数和 since_minutes）。
    """
    claim_token = (request.args.get("claim_token") or "").strip() or None
    raw_email = (request.args.get("email") or "").strip()
    email_addr = normalize_alias_email(raw_email) if raw_email else ""

    # PR#27: 使用 resolve_external_mail_scope 统一处理 claim_token + email
    email_addr, baseline_timestamp = external_api_service.resolve_external_mail_scope(
        email_addr if email_addr else None,
        claim_token,
    )

    folder = (request.args.get("folder") or "inbox").strip().lower() or "inbox"
    if folder not in {"inbox", "junkemail", "deleteditems"}:
        raise external_api_service.InvalidParamError("folder 参数无效")

    def _int_arg(name: str, default: int) -> int:
        raw = request.args.get(name, None)
        if raw is None or raw == "":
            return default
        try:
            return int(raw)
        except Exception as exc:
            raise external_api_service.InvalidParamError(f"{name} 参数无效") from exc

    skip = _int_arg("skip", 0)
    top = _int_arg("top", 20)
    if skip < 0:
        raise external_api_service.InvalidParamError("skip 参数无效")
    if top < 1 or top > 50:
        raise external_api_service.InvalidParamError("top 参数无效")

    since_minutes_raw = request.args.get("since_minutes", None)
    since_minutes = default_since_minutes
    if since_minutes_raw not in (None, ""):
        try:
            since_minutes = int(since_minutes_raw)
        except Exception as exc:
            raise external_api_service.InvalidParamError("since_minutes 参数无效") from exc
        if since_minutes < 1:
            raise external_api_service.InvalidParamError("since_minutes 参数无效")

    return {
        "email": email_addr,
        "folder": folder,
        "skip": skip,
        "top": top,
        "from_contains": (request.args.get("from_contains") or "").strip(),
        "subject_contains": (request.args.get("subject_contains") or "").strip(),
        "since_minutes": since_minutes,
        "claim_token": claim_token,
        "baseline_timestamp": baseline_timestamp,
    }

def _resolve_external_error(
    exc: external_api_service.ExternalApiError, *, allow_nested_upstream: bool = False
) -> dict[str, Any]:
    resolved_code = str(exc.code)
    resolved_message = str(exc.message)
    resolved_status = int(exc.status)

    nested_error = exc.data if isinstance(exc.data, dict) else None
    if allow_nested_upstream and isinstance(exc, external_api_service.UpstreamReadFailedError) and nested_error:
        nested_code = str(nested_error.get("code") or "").strip().upper()
        if nested_code in _EXTERNAL_NESTED_UPSTREAM_CODES:
            resolved_code = nested_code
            resolved_message = str(nested_error.get("message") or exc.message)
            try:
                resolved_status = int(nested_error.get("status") or exc.status)
            except Exception:
                resolved_status = int(exc.status)

    return {
        "code": resolved_code,
        "message": resolved_message,
        "status": resolved_status,
        "data": exc.data,
    }

def _external_error_response(exc: external_api_service.ExternalApiError, *, allow_nested_upstream: bool = False):
    resolved = _resolve_external_error(exc, allow_nested_upstream=allow_nested_upstream)
    return jsonify(external_api_service.fail(resolved["code"], resolved["message"], data=resolved["data"])), resolved["status"]

def _should_return_email_not_found_for_web_extract(exc: external_api_service.ExternalApiError) -> bool:
    # Web 端提取时：只有当所有渠道都是"无邮件"（非鉴权失败/非连接错误）才返回 EMAIL_NOT_FOUND
    # 鉴权失败等错误需要透传原始 code，引导用户重新授权而非误报"无邮件"
    if not isinstance(exc, external_api_service.UpstreamReadFailedError):
        return False

    details = exc.data if isinstance(exc.data, dict) else None
    if not details:
        return False

    channel_errors = [item for item in details.values() if isinstance(item, dict)]
    if not channel_errors:
        channel_errors = [details]

    for item in channel_errors:
        code = str(item.get("code") or "").strip().upper()
        try:
            status = int(item.get("status") or 0)
        except Exception:
            status = 0
        if code in {"IMAP_AUTH_FAILED", "IMAP_CONNECT_FAILED", "IMAP_FOLDER_NOT_FOUND", "ACCOUNT_AUTH_EXPIRED"}:
            return False
        if status in {401, 403}:
            return False

    return True
