from __future__ import annotations

import copy
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from flask import Response, g, jsonify, request

from mailops import config
from mailops.audit import log_audit
from mailops.db import get_db
from mailops.errors import (
    build_error_payload,
    build_error_response,
    build_export_verify_failure_response,
)
from mailops.repositories import accounts as accounts_repo
from mailops.repositories import groups as groups_repo
from mailops.repositories import refresh_logs as refresh_logs_repo
from mailops.repositories import settings as settings_repo
from mailops.repositories import tags as tags_repo
from mailops.repositories.distributed_locks import (
    acquire_distributed_lock,
    release_distributed_lock,
)
from mailops.repositories.refresh_runs import create_refresh_run, finish_refresh_run
from mailops.security.auth import get_client_ip, get_user_agent, login_required
from mailops.security.crypto import decrypt_data
from mailops.services import graph as graph_service
from mailops.services import refresh as refresh_service
from mailops.services.account_import_export import (
    _is_outlook_basic_auth_target,
    _looks_like_imap_host,
    _outlook_basic_auth_import_error,
    _parse_imap_port,
)

from .helpers import (
    _api_update_account_status,
    _build_account_import_failure_response,
    _handle_auto_import,
    _parse_bool_flag,
    sanitize_input,
)


@login_required
def api_add_account() -> Any:
    """添加账号"""
    data = request.json or {}
    account_str = data.get("account_string", "")
    group_id = data.get("group_id", 1)
    provider = (data.get("provider") or "outlook").strip().lower()
    custom_imap_host = (data.get("imap_host") or "").strip()
    custom_imap_port = data.get("imap_port")
    add_to_pool = _parse_bool_flag(data.get("add_to_pool"), default=False)

    if not account_str:
        return build_error_response(
            "ACCOUNT_IMPORT_INPUT_REQUIRED",
            "请输入账号信息",
            message_en="Please enter account information",
        )

    # FD-00006: auto 模式允许 group_id=null（自动分组），需在分组校验前分流
    if provider == "auto":
        return _handle_auto_import(data, add_to_pool=add_to_pool)

    # 校验分组
    target_group = groups_repo.get_group_by_id(group_id)
    if not target_group:
        return build_error_response("GROUP_NOT_FOUND", "分组不存在", message_en="Group not found", status=404)
    if target_group.get("is_system"):
        return build_error_response(
            "SYSTEM_GROUP_PROTECTED",
            "不能导入到系统分组",
            message_en="Cannot import accounts into a system group",
            status=403,
        )

    def sanitize_credential_field(value: Any, max_length: int) -> str:
        if value is None:
            return ""
        text = str(value)
        text = text.replace("\r", "").replace("\n", "").replace("\t", "")
        text = text.strip()
        if len(text) > max_length:
            text = text[:max_length]
        # 移除不可见控制字符
        text = "".join(ch for ch in text if ch.isprintable())
        return text

    def parse_account_string(line: str) -> Optional[Dict[str, str]]:
        """解析账号字符串（格式：email----password----client_id----refresh_token）"""
        parts = line.strip().split("----")
        if len(parts) >= 4:
            return {
                "email": parts[0].strip(),
                "password": parts[1],
                "client_id": parts[2].strip(),
                # refresh_token 可能包含 '----'，这里把剩余部分合并回去
                "refresh_token": "----".join(parts[3:]).strip(),
            }
        return None

    def is_comment_line(line: str) -> bool:
        return bool(line) and line.lstrip().startswith("#")

    # 支持批量导入（多行）+ 逐行校验与错误定位
    raw_lines = account_str.splitlines()
    imported = 0
    failed = 0
    errors: List[Dict[str, Any]] = []
    errors_total = 0
    max_error_details = 50

    db = get_db()

    # -------------------- IMAP provider 导入分支 --------------------
    # 对齐：PRD-00005 / FD-00005 / TDD-00005
    # 约束：不改动 Outlook 旧格式；IMAP 账号使用 client_id/refresh_token 空字符串占位（DB NOT NULL 约束不变）。
    if provider and provider != "outlook":
        from mailops.services.providers import MAIL_PROVIDERS

        provider_cfg = MAIL_PROVIDERS.get(provider, {})
        default_imap_host = (provider_cfg.get("imap_host") or "").strip()
        default_imap_port = int(provider_cfg.get("imap_port") or 993)

        # custom 可从 request body 提供全局 host/port（兼容前端“自定义 IMAP 配置”输入）
        if provider == "custom":
            if custom_imap_port is None or str(custom_imap_port).strip() == "":
                custom_port_val = 993
            else:
                custom_port_val = _parse_imap_port(custom_imap_port)
                if custom_port_val is None:
                    return build_error_response(
                        "INVALID_PARAM",
                        "自定义 IMAP 端口无效，应为 1-65535",
                        message_en="Custom IMAP port is invalid. Expected 1-65535",
                        status=400,
                    )
        else:
            custom_port_val = None

        for line_no, raw in enumerate(raw_lines, start=1):
            line = (raw or "").strip()
            if not line or is_comment_line(line):
                continue

            parts = [p.strip() for p in line.split("----")]
            email_addr = sanitize_credential_field(parts[0] if len(parts) > 0 else "", 320)
            imap_pwd = sanitize_credential_field(parts[1] if len(parts) > 1 else "", 500)

            if len(parts) < 2 or not email_addr or not imap_pwd:
                failed += 1
                errors_total += 1
                if len(errors) < max_error_details:
                    errors.append(
                        {
                            "line": line_no,
                            "email": email_addr,
                            "error": "格式错误，应为：邮箱----IMAP授权码/应用密码（custom 可包含 host/port）",
                        }
                    )
                continue

            # 基础邮箱格式校验
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_addr):
                failed += 1
                errors_total += 1
                if len(errors) < max_error_details:
                    errors.append(
                        {
                            "line": line_no,
                            "email": email_addr,
                            "error": "邮箱格式不正确",
                        }
                    )
                continue

            imap_host = default_imap_host
            imap_port = default_imap_port

            if provider == "custom":
                # 兼容两类输入：
                # 1) 5 段（导出格式）：email----imap_password----custom----imap_host----imap_port
                # 2) 4 段（文本批量）：email----imap_password----imap_host----imap_port
                # 3) 2 段（配合输入框）：email----imap_password（host/port 从 request body 取）
                if len(parts) >= 5 and (parts[2] or "").strip().lower() == "custom":
                    imap_host = (parts[3] or "").strip()
                    raw_port = (parts[4] or "").strip()
                    if not raw_port:
                        failed += 1
                        errors_total += 1
                        if len(errors) < max_error_details:
                            errors.append(
                                {
                                    "line": line_no,
                                    "email": email_addr,
                                    "error": "custom 5段格式缺少 IMAP 端口",
                                }
                            )
                        continue
                    imap_port = _parse_imap_port(raw_port)
                    if imap_port is None:
                        failed += 1
                        errors_total += 1
                        if len(errors) < max_error_details:
                            errors.append(
                                {
                                    "line": line_no,
                                    "email": email_addr,
                                    "error": "custom IMAP 端口无效，应为 1-65535",
                                }
                            )
                        continue
                elif len(parts) >= 4:
                    imap_host = (parts[2] or "").strip()
                    raw_port = (parts[3] or "").strip()
                    if not raw_port:
                        failed += 1
                        errors_total += 1
                        if len(errors) < max_error_details:
                            errors.append(
                                {
                                    "line": line_no,
                                    "email": email_addr,
                                    "error": "custom 4段格式缺少 IMAP 端口",
                                }
                            )
                        continue
                    imap_port = _parse_imap_port(raw_port)
                    if imap_port is None:
                        failed += 1
                        errors_total += 1
                        if len(errors) < max_error_details:
                            errors.append(
                                {
                                    "line": line_no,
                                    "email": email_addr,
                                    "error": "custom IMAP 端口无效，应为 1-65535",
                                }
                            )
                        continue
                else:
                    imap_host = custom_imap_host
                    imap_port = custom_port_val if custom_port_val is not None else 993

                if not imap_host:
                    failed += 1
                    errors_total += 1
                    if len(errors) < max_error_details:
                        errors.append(
                            {
                                "line": line_no,
                                "email": email_addr,
                                "error": "自定义 IMAP 必须提供服务器地址（imap_host）",
                            }
                        )
                    continue
            else:
                # 兼容导出格式：email----imap_password----provider
                if len(parts) >= 3:
                    line_provider = (parts[2] or "").strip().lower()
                    if line_provider and line_provider != provider:
                        # 明确不一致：提示用户切换 provider 或修正文本
                        failed += 1
                        errors_total += 1
                        if len(errors) < max_error_details:
                            errors.append(
                                {
                                    "line": line_no,
                                    "email": email_addr,
                                    "error": f"provider 不匹配：当前选择 {provider}，文本为 {line_provider}",
                                }
                            )
                        continue

                if not imap_host:
                    failed += 1
                    errors_total += 1
                    if len(errors) < max_error_details:
                        errors.append(
                            {
                                "line": line_no,
                                "email": email_addr,
                                "error": "未找到该 provider 的默认 IMAP 配置，请使用自定义 IMAP",
                            }
                        )
                    continue

            if _is_outlook_basic_auth_target(email_addr, imap_host, provider):
                failed += 1
                errors_total += 1
                if len(errors) < max_error_details:
                    errors.append(
                        {
                            "line": line_no,
                            "email": email_addr,
                            "error": _outlook_basic_auth_import_error(),
                        }
                    )
                continue

            ok = accounts_repo.add_account(
                email_addr,
                password="",
                client_id="",
                refresh_token="",
                group_id=group_id,
                remark="",
                account_type="imap",
                provider=provider,
                imap_host=imap_host,
                imap_port=imap_port,
                imap_password=imap_pwd,
                add_to_pool=add_to_pool,
                db=db,
                commit=False,
            )
            if ok:
                imported += 1
                continue

            failed += 1
            errors_total += 1
            reason = "写入失败"
            try:
                exists = db.execute("SELECT 1 FROM accounts WHERE email = ? LIMIT 1", (email_addr,)).fetchone()
                if exists:
                    reason = "邮箱已存在"
            except Exception:
                pass
            if len(errors) < max_error_details:
                errors.append({"line": line_no, "email": email_addr, "error": reason})

        summary = {
            "group_id": group_id,
            "total_lines": len(raw_lines),
            "imported": imported,
            "failed": failed,
            "errors_total": errors_total,
            "errors_returned": len(errors),
            "errors_truncated": errors_total > len(errors),
        }

        message = f"导入完成：成功 {imported} 个，失败 {failed} 个"

        if imported > 0:
            try:
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                return build_error_response(
                    "ACCOUNT_IMPORT_DB_WRITE_FAILED",
                    "数据库写入失败，请重试",
                    message_en="Database write failed. Please try again",
                    status=500,
                )
            log_audit(
                "import",
                "account",
                None,
                f"{message}，目标分组ID={group_id}，provider={provider}",
            )
            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "summary": summary,
                    "errors": errors,
                }
            )

        return _build_account_import_failure_response(message, summary=summary, errors=errors)

    # -------------------- Outlook（旧格式）导入分支：保持现有逻辑完全不动 --------------------
    for line_no, raw in enumerate(raw_lines, start=1):
        line = (raw or "").strip()
        if not line:
            continue
        if is_comment_line(line):
            continue

        parsed = parse_account_string(line)
        if not parsed:
            failed += 1
            errors_total += 1
            if len(errors) < max_error_details:
                errors.append(
                    {
                        "line": line_no,
                        "error": "格式错误，应为：邮箱----密码----client_id----refresh_token",
                    }
                )
            continue

        email_addr = sanitize_credential_field(parsed.get("email"), 320)
        password = sanitize_credential_field(parsed.get("password"), 500)
        client_id = sanitize_credential_field(parsed.get("client_id"), 200)
        refresh_token = sanitize_credential_field(parsed.get("refresh_token"), 4096)

        if not email_addr or not client_id or not refresh_token:
            failed += 1
            errors_total += 1
            if len(errors) < max_error_details:
                errors.append(
                    {
                        "line": line_no,
                        "email": email_addr,
                        "error": "邮箱、Client ID、Refresh Token 不能为空",
                    }
                )
            continue

        # 基础邮箱格式校验
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_addr):
            failed += 1
            errors_total += 1
            if len(errors) < max_error_details:
                errors.append({"line": line_no, "email": email_addr, "error": "邮箱格式不正确"})
            continue

        ok = accounts_repo.add_account(
            email_addr,
            password,
            client_id,
            refresh_token,
            group_id,
            add_to_pool=add_to_pool,
            db=db,
            commit=False,
        )
        if ok:
            imported += 1
            continue

        failed += 1
        errors_total += 1
        reason = "写入失败"
        try:
            exists = db.execute("SELECT 1 FROM accounts WHERE email = ? LIMIT 1", (email_addr,)).fetchone()
            if exists:
                reason = "邮箱已存在"
        except Exception:
            pass
        if len(errors) < max_error_details:
            errors.append({"line": line_no, "email": email_addr, "error": reason})

    summary = {
        "group_id": group_id,
        "total_lines": len(raw_lines),
        "imported": imported,
        "failed": failed,
        "errors_total": errors_total,
        "errors_returned": len(errors),
        "errors_truncated": errors_total > len(errors),
    }

    message = f"导入完成：成功 {imported} 个，失败 {failed} 个"

    if imported > 0:
        try:
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return build_error_response(
                "ACCOUNT_IMPORT_DB_WRITE_FAILED",
                "数据库写入失败，请重试",
                message_en="Database write failed. Please try again",
                status=500,
            )
        log_audit("import", "account", None, f"{message}，目标分组ID={group_id}")
        return jsonify({"success": True, "message": message, "summary": summary, "errors": errors})

    return _build_account_import_failure_response(message, summary=summary, errors=errors)


@login_required
def api_update_account(account_id: int) -> Any:
    """更新账号（邮箱池管理的 CF 临时邮箱不允许手动编辑）"""
    # 邮箱池管理的 CF 临时邮箱不允许手动编辑
    db = get_db()
    cf_row = db.execute("SELECT provider FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if cf_row and (cf_row["provider"] or "").lower() == "cloudflare_temp_mail":
        return build_error_response(
            "POOL_ACCOUNT_UPDATE_DENIED",
            "邮箱池管理的 CF 临时邮箱不允许手动编辑",
            message_en="CF temp mail accounts managed by pool cannot be edited manually.",
            status=403,
        )

    data = request.json

    # 检查是否只更新状态
    if "status" in data and len(data) == 1:
        # 只更新状态
        return _api_update_account_status(account_id, data["status"])

    email_addr = (data.get("email") or "").strip()
    password = data.get("password")
    client_id = data.get("client_id")
    refresh_token = data.get("refresh_token")
    try:
        group_id = int(data.get("group_id", 1) or 1)
    except Exception:
        group_id = 1
    remark = sanitize_input(data.get("remark", ""), max_length=200)
    status = data.get("status", "active")

    if not email_addr:
        return build_error_response(
            "ACCOUNT_EMAIL_REQUIRED",
            "邮箱不能为空",
            message_en="Email address is required",
        )

    target_group = groups_repo.get_group_by_id(group_id)
    if not target_group:
        error_payload = build_error_payload(
            code="GROUP_NOT_FOUND",
            message="分组不存在",
            err_type="NotFoundError",
            status=404,
            details=f"group_id={group_id}",
        )
        return jsonify({"success": False, "error": error_payload}), 404

    if target_group.get("is_system"):
        error_payload = build_error_payload(
            code="SYSTEM_GROUP_PROTECTED",
            message="不能移动到系统分组",
            err_type="ForbiddenError",
            status=403,
            details=f"group_id={group_id}",
        )
        return jsonify({"success": False, "error": error_payload}), 403

    existing_account = accounts_repo.get_account_by_id(account_id)
    if not existing_account:
        return build_error_response(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            message_en="Account not found",
            status=404,
        )

    account_type = (existing_account.get("account_type") or "outlook").strip().lower()
    if account_type != "imap":
        submitted_client_id = client_id.strip() if isinstance(client_id, str) else ""
        submitted_refresh_token = refresh_token.strip() if isinstance(refresh_token, str) else ""
        existing_client_id = (existing_account.get("client_id") or "").strip()
        client_id_changed = bool(submitted_client_id) and submitted_client_id != existing_client_id

        if client_id_changed and not submitted_refresh_token:
            return build_error_response(
                "OUTLOOK_REFRESH_TOKEN_REQUIRED",
                "修改 Client ID 时必须同时提供 Refresh Token",
                message_en="Refresh Token is required when changing Client ID",
                status=400,
            )

    if accounts_repo.update_account(
        account_id,
        email_addr,
        password,
        client_id,
        refresh_token,
        group_id,
        remark,
        status,
    ):
        changed_fields = []
        if isinstance(client_id, str) and client_id.strip():
            changed_fields.append("client_id")
        if isinstance(password, str) and password.strip():
            changed_fields.append("password")
        if isinstance(refresh_token, str) and refresh_token.strip():
            changed_fields.append("refresh_token")
        details = json.dumps(
            {
                "email": email_addr,
                "group_id": group_id,
                "status": status,
                "changed_fields": changed_fields,
            },
            ensure_ascii=False,
        )
        log_audit("update", "account", str(account_id), details)
        return jsonify(
            {
                "success": True,
                "message": "账号更新成功",
                "message_en": "Account updated successfully",
            }
        )
    return build_error_response(
        "ACCOUNT_UPDATE_FAILED",
        "更新失败",
        message_en="Failed to update account",
        status=500,
    )


@login_required
def api_update_account_remark(account_id: int) -> Any:
    """仅更新账号备注，不要求重复提交其他字段。"""
    data = request.get_json(silent=True) or {}
    remark = sanitize_input(data.get("remark", ""), max_length=200)

    existing_account = accounts_repo.get_account_by_id(account_id)
    if not existing_account:
        return build_error_response(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            message_en="Account not found",
            status=404,
        )

    email_addr = (existing_account.get("email") or "").strip()
    password = None
    client_id = existing_account.get("client_id")
    refresh_token = None
    group_id = int(existing_account.get("group_id") or 1)
    status = existing_account.get("status") or "active"

    if not accounts_repo.update_account(
        account_id,
        email_addr,
        password,
        client_id,
        refresh_token,
        group_id,
        remark,
        status,
    ):
        return build_error_response(
            "ACCOUNT_UPDATE_FAILED",
            "更新失败",
            message_en="Failed to update account",
            status=500,
        )

    log_audit(
        "update",
        "account",
        str(account_id),
        json.dumps({"remark": remark}, ensure_ascii=False),
    )
    return jsonify(
        {
            "success": True,
            "message": "备注更新成功",
            "message_en": "Remark updated successfully",
        }
    )


@login_required
def api_delete_account(account_id: int) -> Any:
    """删除账号（邮箱池管理的 CF 临时邮箱不允许手动删除）"""
    email_addr = ""
    try:
        db = get_db()
        row = db.execute("SELECT email, provider FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row:
            email_addr = row["email"]
            # 邮箱池管理的 CF 临时邮箱不允许手动删除
            if (row["provider"] or "").lower() == "cloudflare_temp_mail":
                return build_error_response(
                    "POOL_ACCOUNT_DELETE_DENIED",
                    "邮箱池管理的 CF 临时邮箱不允许手动删除，请通过邮箱池接口释放",
                    message_en="CF temp mail accounts managed by pool cannot be deleted manually. Use pool release API instead.",
                    status=403,
                )
    except Exception:
        email_addr = ""
    if accounts_repo.delete_account_by_id(account_id):
        log_audit(
            "delete",
            "account",
            str(account_id),
            f"删除账号：{email_addr}" if email_addr else "删除账号",
        )
        return jsonify({"success": True})
    return build_error_response(
        "ACCOUNT_DELETE_FAILED",
        "删除失败",
        message_en="Failed to delete account",
        status=500,
    )


@login_required
def api_delete_account_by_email(email_addr: str) -> Any:
    """根据邮箱地址删除账号（邮箱池管理的 CF 临时邮箱不允许手动删除）"""
    db = get_db()
    row = db.execute("SELECT provider FROM accounts WHERE email = ?", (email_addr,)).fetchone()
    if row and (row["provider"] or "").lower() == "cloudflare_temp_mail":
        return build_error_response(
            "POOL_ACCOUNT_DELETE_DENIED",
            "邮箱池管理的 CF 临时邮箱不允许手动删除，请通过邮箱池接口释放",
            message_en="CF temp mail accounts managed by pool cannot be deleted manually. Use pool release API instead.",
            status=403,
        )
    if accounts_repo.delete_account_by_email(email_addr):
        log_audit("delete", "account", email_addr, f"删除账号：{email_addr}")
        return jsonify({"success": True})
    return build_error_response(
        "ACCOUNT_DELETE_FAILED",
        "删除失败",
        message_en="Failed to delete account",
        status=500,
    )
