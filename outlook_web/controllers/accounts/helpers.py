from __future__ import annotations

import copy
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from flask import Response, g, jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.db import get_db
from outlook_web.errors import (
    build_error_payload,
    build_error_response,
    build_export_verify_failure_response,
)
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import groups as groups_repo
from outlook_web.repositories import refresh_logs as refresh_logs_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.repositories import tags as tags_repo
from outlook_web.repositories.distributed_locks import (
    acquire_distributed_lock,
    release_distributed_lock,
)
from outlook_web.repositories.refresh_runs import create_refresh_run, finish_refresh_run
from outlook_web.security.auth import get_client_ip, get_user_agent, login_required
from outlook_web.security.crypto import decrypt_data
from outlook_web.services import graph as graph_service
from outlook_web.services import refresh as refresh_service
from outlook_web.services.account_import_export import (
    _build_export_text,
    _detect_line_type,
    _is_outlook_basic_auth_target,
    _looks_like_imap_host,
    _outlook_basic_auth_import_error,
    _parse_imap_port,
)


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    净化用户输入，防止XSS攻击
    - 转义HTML特殊字符
    - 限制长度
    - 移除控制字符
    """
    if not text:
        return ""

    # 限制长度
    text = text[:max_length]

    # 移除控制字符（保留换行和制表符）
    text = "".join(char for char in text if char.isprintable() or char in "\n\t")

    # 转义HTML特殊字符
    text = html.escape(text, quote=True)

    return text


def _parse_bool_flag(value: Any, default: bool = False) -> bool:
    """解析请求中的布尔开关，兼容 bool / 数字 / 字符串。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_account_status(status: Any) -> Optional[str]:
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in {"active", "inactive", "disabled"}:
        return None
    return normalized_status


def _build_account_import_failure_response(
    message: str,
    *,
    summary: dict[str, Any],
    errors: list[dict[str, Any]],
):
    return build_error_response(
        "ACCOUNT_IMPORT_FAILED",
        message,
        message_en="Account import failed",
        status=400,
        extra={"summary": summary, "errors": errors},
    )


# ==================== 账号基础 CRUD API ====================


def _resolve_auto_group(
    provider: str,
    group_cache: Dict[str, int],
    groups_created: List[str],
) -> int:
    """根据 provider 查找或创建分组，使用缓存避免重复查询。"""
    from outlook_web.services.providers import PROVIDER_GROUP_NAME

    if provider in group_cache:
        return group_cache[provider]

    group_name = PROVIDER_GROUP_NAME.get(provider, provider)
    existing = groups_repo.get_group_by_name(group_name)
    if existing:
        group_cache[provider] = existing["id"]
        return existing["id"]

    new_id = groups_repo.add_group(group_name)
    if new_id:
        group_cache[provider] = new_id
        groups_created.append(group_name)
        return new_id

    # 创建失败时尝试再次查找（可能并发创建）
    existing = groups_repo.get_group_by_name(group_name)
    if existing:
        group_cache[provider] = existing["id"]
        return existing["id"]

    # 兜底：使用默认分组
    default_id = groups_repo.get_default_group_id()
    group_cache[provider] = default_id
    return default_id


def _overwrite_account(existing: Dict, detect_result: Dict, group_id: int, add_to_pool: bool = False) -> bool:
    """覆盖更新已存在账号的凭据字段，保留 remark/tags/status。"""
    fields: Dict[str, Any] = {"group_id": group_id}
    d = detect_result
    prov = d["provider"]
    f = d["fields"]

    if d["type"] == "outlook":
        fields["password"] = f.get("password", "")
        fields["client_id"] = f.get("client_id", "")
        fields["refresh_token"] = f.get("refresh_token", "")
        fields["account_type"] = "outlook"
        fields["provider"] = "outlook"
    elif d["type"] == "imap":
        fields["imap_password"] = f.get("imap_password", "")
        fields["imap_host"] = f.get("imap_host", "")
        fields["imap_port"] = f.get("imap_port", 993)
        fields["account_type"] = "imap"
        fields["provider"] = prov

    # 若勾选了"加入邮箱池"且该账号尚未处于 available 状态（含 NULL / claimed 等），则同步设置 pool_status
    if add_to_pool and existing.get("pool_status") != "available":
        fields["pool_status"] = "available"

    return accounts_repo.update_account_credentials(existing["id"], **fields)


def _handle_temp_mail_import(
    email: str,
    errors: List[Dict[str, Any]],
    line_num: int,
    temp_mail_count: int,
    max_temp_mail: int = 20,
) -> bool:
    """处理临时邮箱的导入，写入 temp_emails 表。"""
    from outlook_web.repositories import temp_emails as temp_emails_repo
    from outlook_web.services.temp_mail_service import (
        TEMP_MAIL_SOURCE,
        get_temp_mail_service,
    )

    if temp_mail_count >= max_temp_mail:
        errors.append(
            {
                "line": line_num,
                "email": email,
                "error": f"临时邮箱单次导入上限 {max_temp_mail} 个",
                "detected_type": "temp_mail",
            }
        )
        return False

    # 检查是否已存在
    existing = temp_emails_repo.get_temp_email_by_address(email)
    if existing:
        return True  # 已存在视为跳过（成功）

    # BUG-02: 严格导入（不做本地兜底写入）
    temp_mail_service = get_temp_mail_service()
    try:
        mailbox = temp_mail_service.import_user_mailbox(email, allow_local_fallback=False)
    except Exception as exc:
        errors.append(
            {
                "line": line_num,
                "email": email,
                "error": f"临时邮箱导入失败：{str(exc) or '上游探测失败'}",
                "detected_type": "temp_mail",
            }
        )
        return False

    actual_email = str((mailbox or {}).get("email") or "").strip() or email
    # 导入成功后应已落库；这里做一次确认
    if temp_emails_repo.get_temp_email_by_address(actual_email):
        return True
    errors.append(
        {
            "line": line_num,
            "email": email,
            "error": "临时邮箱导入失败：导入未落库",
            "detected_type": "temp_mail",
        }
    )
    return False


def _handle_auto_import(data: Dict[str, Any], *, add_to_pool: bool = False) -> Any:
    """处理 provider="auto" 的智能混合导入。"""
    account_str = data.get("account_string", "")
    duplicate_strategy = (data.get("duplicate_strategy") or "skip").strip().lower()
    if duplicate_strategy not in ("skip", "overwrite"):
        duplicate_strategy = "skip"
    fallback_host = (data.get("imap_host") or "").strip()
    try:
        fallback_port = int(data.get("imap_port") or 993)
    except Exception:
        fallback_port = 993
    explicit_group_id = data.get("group_id")

    # 验证显式 group_id（如果提供）
    use_auto_group = explicit_group_id is None
    if not use_auto_group:
        try:
            explicit_group_id = int(explicit_group_id)
        except Exception:
            explicit_group_id = None
            use_auto_group = True
        if explicit_group_id is not None:
            target_group = groups_repo.get_group_by_id(explicit_group_id)
            if not target_group:
                return build_error_response(
                    "GROUP_NOT_FOUND",
                    "指定的分组不存在",
                    message_en="Target group not found",
                    status=404,
                )
            if target_group.get("is_system"):
                return build_error_response(
                    "SYSTEM_GROUP_PROTECTED",
                    "不能导入到系统分组",
                    message_en="Cannot import accounts into a system group",
                    status=403,
                )

    raw_lines = account_str.splitlines()

    # 合并续行：从其他地方复制的凭据中 refresh_token 可能包含换行符（行宽折行），
    # splitlines() 会将其切碎；续行特征：不含 '----' 分隔符且不是注释行
    _merged: list[str] = []
    for _line in raw_lines:
        _stripped = _line.strip()
        if not _stripped:
            continue
        if _merged and not _merged[-1].lstrip().startswith("#") and "----" not in _stripped and not _stripped.startswith("#"):
            _merged[-1] += _stripped
        else:
            _merged.append(_stripped)
    raw_lines = _merged

    imported = 0
    skipped = 0
    failed = 0
    by_provider: Dict[str, Dict[str, int]] = {}
    groups_created: List[str] = []
    errors: List[Dict[str, Any]] = []
    errors_total = 0
    max_error_details = 50
    group_cache: Dict[str, int] = {}
    temp_mail_count = 0

    for line_num, raw in enumerate(raw_lines, 1):
        line = (raw or "").strip()
        if not line or line.startswith("#"):
            continue

        result = _detect_line_type(line, fallback_host, fallback_port)

        if result["type"] == "error":
            failed += 1
            errors_total += 1
            if len(errors) < max_error_details:
                errors.append({"line": line_num, "email": "", "error": result["error"]})
            continue

        fields = result["fields"]
        email = fields.get("email", "").strip()
        prov = result["provider"]

        # 邮箱格式校验
        if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            failed += 1
            errors_total += 1
            if len(errors) < max_error_details:
                errors.append(
                    {
                        "line": line_num,
                        "email": email,
                        "error": "邮箱格式不正确",
                        "detected_type": result["type"],
                    }
                )
            continue

        # 初始化 provider 统计
        if prov not in by_provider:
            by_provider[prov] = {"imported": 0, "skipped": 0, "failed": 0}

        # 临时邮箱特殊处理：写入 temp_emails
        if result["type"] == "temp_mail":
            from outlook_web.repositories import temp_emails as temp_emails_repo

            existing_temp = temp_emails_repo.get_temp_email_by_address(email)
            if existing_temp:
                if duplicate_strategy == "skip":
                    skipped += 1
                    by_provider[prov]["skipped"] += 1
                    continue
                # overwrite 对临时邮箱无意义（无凭据可更新），视为跳过
                skipped += 1
                by_provider[prov]["skipped"] += 1
                continue

            ok = _handle_temp_mail_import(email, errors, line_num, temp_mail_count)
            if ok:
                imported += 1
                temp_mail_count += 1
                by_provider[prov]["imported"] += 1
            else:
                failed += 1
                errors_total += 1
                by_provider[prov]["failed"] += 1
            continue

        # 解析分组（Outlook/IMAP）
        if use_auto_group:
            group_id = _resolve_auto_group(prov, group_cache, groups_created)
        else:
            group_id = explicit_group_id

        # 检查重复
        existing = accounts_repo.get_account_by_email(email)
        if existing:
            if duplicate_strategy == "skip":
                skipped += 1
                by_provider[prov]["skipped"] += 1
                continue
            elif duplicate_strategy == "overwrite":
                ok = _overwrite_account(existing, result, group_id, add_to_pool=add_to_pool)
                if ok:
                    imported += 1
                    by_provider[prov]["imported"] += 1
                    log_audit(
                        "overwrite",
                        "account",
                        str(existing["id"]),
                        f"覆盖更新 email={email}, provider={prov}",
                    )
                else:
                    failed += 1
                    errors_total += 1
                    by_provider[prov]["failed"] += 1
                    if len(errors) < max_error_details:
                        errors.append(
                            {
                                "line": line_num,
                                "email": email,
                                "error": "覆盖更新失败",
                                "detected_type": result["type"],
                            }
                        )
                continue

        # 新增账号
        if result["type"] == "outlook":
            ok = accounts_repo.add_account(
                email_addr=email,
                password=fields.get("password", ""),
                client_id=fields.get("client_id", ""),
                refresh_token=fields.get("refresh_token", ""),
                group_id=group_id,
                account_type="outlook",
                provider="outlook",
                add_to_pool=add_to_pool,
            )
        elif result["type"] == "imap":
            ok = accounts_repo.add_account(
                email_addr=email,
                password="",
                client_id="",
                refresh_token="",
                group_id=group_id,
                account_type="imap",
                provider=prov,
                imap_host=fields.get("imap_host", ""),
                imap_port=fields.get("imap_port", 993),
                imap_password=fields.get("imap_password", ""),
                add_to_pool=add_to_pool,
            )
        else:
            ok = False

        if ok:
            imported += 1
            by_provider[prov]["imported"] += 1
        else:
            failed += 1
            errors_total += 1
            by_provider[prov]["failed"] += 1
            reason = "写入失败"
            try:
                exists = get_db().execute("SELECT 1 FROM accounts WHERE email = ? LIMIT 1", (email,)).fetchone()
                if exists:
                    reason = "邮箱已存在"
            except Exception:
                pass
            if len(errors) < max_error_details:
                errors.append(
                    {
                        "line": line_num,
                        "email": email,
                        "error": reason,
                        "detected_type": result["type"],
                    }
                )

    summary = {
        "mode": "auto",
        "total_lines": len(raw_lines),
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "by_provider": by_provider,
        "groups_created": groups_created,
        "duplicate_strategy": duplicate_strategy,
        "errors_total": errors_total,
        "errors_returned": len(errors),
        "errors_truncated": errors_total > len(errors),
    }

    success = imported > 0 or skipped > 0
    message = f"混合导入完成：成功 {imported} 个，跳过 {skipped} 个，失败 {failed} 个"

    if imported > 0 or skipped > 0:
        log_audit(
            "import",
            "account",
            None,
            f"{message}，mode=auto，duplicate_strategy={duplicate_strategy}",
        )

    return jsonify({"success": success, "message": message, "summary": summary, "errors": errors})


def _api_update_account_status(account_id: int, status: str) -> Any:
    """只更新账号状态"""
    normalized_status = _normalize_account_status(status)
    if not normalized_status:
        return build_error_response(
            "INVALID_PARAM",
            "状态值无效",
            message_en="Invalid account status",
            status=400,
        )

    db = get_db()
    try:
        cursor = db.execute(
            """
            UPDATE accounts
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (normalized_status, account_id),
        )
        db.commit()
        if cursor.rowcount <= 0:
            return build_error_response(
                "ACCOUNT_NOT_FOUND",
                "账号不存在",
                message_en="Account not found",
                status=404,
            )
        return jsonify({"success": True, "message": "状态更新成功"})
    except Exception:
        return build_error_response(
            "ACCOUNT_STATUS_UPDATE_FAILED",
            "更新失败",
            message_en="Failed to update account status",
            status=500,
        )
