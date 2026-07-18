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
from mailops.services.account_import_export import _build_export_text


@login_required
def api_export_all_accounts() -> Any:
    """导出所有邮箱账号为 TXT 文件（需要二次验证）"""
    from mailops.security.auth import (
        consume_export_verify_token,
        get_client_ip,
        get_user_agent,
    )

    # 从请求头获取二次验证 token（避免 URL 泄露）
    verify_token = request.headers.get("X-Export-Token")
    client_ip = get_client_ip()
    user_agent = get_user_agent()

    ok, error_message = consume_export_verify_token(verify_token, client_ip, user_agent)
    if not ok:
        return build_export_verify_failure_response(error_message)

    # 使用 load_accounts 获取所有账号（自动解密）
    accounts = accounts_repo.load_accounts()

    # 加载临时邮箱
    from mailops.repositories import temp_emails as temp_emails_repo

    temp_emails = temp_emails_repo.load_temp_emails()

    if not accounts and not temp_emails:
        return build_error_response(
            "ACCOUNT_EXPORT_EMPTY",
            "没有邮箱账号",
            message_en="No mail accounts are available for export",
            status=404,
        )

    # 记录审计日志
    log_audit(
        "export",
        "all_accounts",
        None,
        f"导出所有账号，共 {len(accounts)} 个账号 + {len(temp_emails)} 个临时邮箱",
    )

    content = _build_export_text(accounts, temp_emails)

    # 生成文件名（使用 URL 编码处理中文）
    filename = f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    encoded_filename = quote(filename)

    # 返回文件下载响应
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@login_required
def api_export_selected_accounts() -> Any:
    """导出选中分组的邮箱账号为 TXT 文件（需要二次验证）"""
    from mailops.security.auth import (
        consume_export_verify_token,
        get_client_ip,
        get_user_agent,
    )

    data = request.json or {}
    group_ids = data.get("group_ids", [])
    verify_token = request.headers.get("X-Export-Token") or data.get("verify_token")
    client_ip = get_client_ip()
    user_agent = get_user_agent()

    ok, error_message = consume_export_verify_token(verify_token, client_ip, user_agent)
    if not ok:
        return build_export_verify_failure_response(error_message)

    if not group_ids:
        return build_error_response(
            "GROUP_IDS_REQUIRED",
            "请选择要导出的分组",
            message_en="Please select at least one group to export",
        )

    # 获取选中分组下的所有账号（使用 load_accounts 自动解密）
    all_accounts = []
    for group_id in group_ids:
        accounts = accounts_repo.load_accounts(group_id)
        all_accounts.extend(accounts)

    # 仅当选中了"临时邮箱"系统分组时才附加临时邮箱
    from mailops.repositories import temp_emails as temp_emails_repo

    temp_emails: List[Dict] = []
    temp_group = groups_repo.get_group_by_name("临时邮箱")
    if temp_group and temp_group["id"] in group_ids:
        temp_emails = temp_emails_repo.load_temp_emails()

    if not all_accounts and not temp_emails:
        return build_error_response(
            "ACCOUNT_EXPORT_EMPTY",
            "选中的分组下没有邮箱账号",
            message_en="No mail accounts were found in the selected groups",
            status=404,
        )

    # 记录审计日志
    log_audit(
        "export",
        "selected_groups",
        ",".join(map(str, group_ids)),
        f"导出选中分组的 {len(all_accounts)} 个账号 + {len(temp_emails)} 个临时邮箱",
    )

    content = _build_export_text(all_accounts, temp_emails)

    # 生成文件名
    filename = f"accounts_export_selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    encoded_filename = quote(filename)

    # 返回文件下载响应
    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@login_required
def api_generate_export_verify_token() -> Any:
    """生成导出验证token（二次验证）"""
    from mailops.repositories import settings as settings_repo
    from mailops.security.auth import (
        get_client_ip,
        get_user_agent,
        issue_export_verify_token,
    )
    from mailops.security.crypto import verify_password

    data = request.json
    password = data.get("password", "")

    # 验证密码
    stored_password = settings_repo.get_login_password()
    if not verify_password(password, stored_password):
        return build_error_response(
            "LOGIN_INVALID_PASSWORD",
            "密码错误",
            message_en="Invalid password",
            status=401,
        )

    # 生成一次性 token
    client_ip = get_client_ip()
    user_agent = get_user_agent()
    verify_token = issue_export_verify_token(client_ip, user_agent)
    return jsonify({"success": True, "verify_token": verify_token})


# ==================== Token 刷新 API ====================
