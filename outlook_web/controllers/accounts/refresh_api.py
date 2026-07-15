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

REFRESH_LOCK_NAME = "refresh_all_tokens"

@login_required
def api_refresh_account(account_id: int) -> Any:
    """刷新单个账号的 token"""
    db = get_db()
    cursor = db.execute(
        "SELECT id, email, client_id, refresh_token, group_id, account_type FROM accounts WHERE id = ?",
        (account_id,),
    )
    account = cursor.fetchone()

    if not account:
        error_payload = build_error_payload(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            "NotFoundError",
            404,
            f"account_id={account_id}",
        )
        return jsonify({"success": False, "error": error_payload})

    account_id = account["id"]
    account_email = account["email"]
    client_id = account["client_id"]
    encrypted_refresh_token = account["refresh_token"]

    if not refresh_service.is_refreshable_outlook_account(account["account_type"]):
        return build_error_response(
            "ACCOUNT_REFRESH_UNSUPPORTED",
            "IMAP 账号不支持 Token 刷新",
            message_en="IMAP accounts do not support token refresh",
            err_type="UnsupportedOperationError",
            status=400,
            details=f"account_id={account_id}, account_type={account['account_type']}",
        )

    # 获取分组代理设置
    proxy_url = ""
    if account["group_id"]:
        group = groups_repo.get_group_by_id(account["group_id"])
        if group:
            proxy_url = group.get("proxy_url", "") or ""

    # 解密 refresh_token
    try:
        refresh_token = decrypt_data(encrypted_refresh_token) if encrypted_refresh_token else encrypted_refresh_token
    except Exception as e:
        error_msg = f"解密 token 失败: {str(e)}"
        refresh_logs_repo.log_refresh_result(account_id, account_email, "manual", "failed", error_msg)
        error_payload = build_error_payload("TOKEN_DECRYPT_FAILED", "Token 解密失败", "DecryptionError", 500, error_msg)
        return jsonify({"success": False, "error": error_payload})

    # 测试 refresh token（并支持滚动更新 refresh_token）
    success, error_msg, new_refresh_token = graph_service.test_refresh_token_with_rotation(client_id, refresh_token, proxy_url)

    # 记录刷新结果
    refresh_logs_repo.log_refresh_result(
        account_id,
        account_email,
        "manual",
        "success" if success else "failed",
        error_msg,
    )

    if success:
        try:
            if isinstance(new_refresh_token, str) and new_refresh_token.strip() and new_refresh_token != refresh_token:
                accounts_repo.update_account_credentials(account_id, refresh_token=new_refresh_token)
            db.execute(
                "UPDATE accounts SET last_refresh_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (account_id,),
            )
            db.commit()
        except Exception:
            pass
        return jsonify({"success": True, "message": "Token 刷新成功"})

    error_payload = build_error_payload(
        "TOKEN_REFRESH_FAILED",
        "Token 刷新失败",
        "RefreshTokenError",
        400,
        error_msg or "未知错误",
    )
    return jsonify({"success": False, "error": error_payload})

@login_required
def api_refresh_all_accounts() -> Any:
    """刷新所有账号的 token（流式响应，实时返回进度）"""
    trace_id_value = None
    try:
        trace_id_value = getattr(g, "trace_id", None)
    except Exception:
        trace_id_value = None
    requested_by_ip = get_client_ip()
    requested_by_user_agent = get_user_agent()

    def generate():
        yield from refresh_service.stream_refresh_all_accounts(
            trace_id=trace_id_value,
            requested_by_ip=requested_by_ip,
            requested_by_user_agent=requested_by_user_agent,
            lock_name=REFRESH_LOCK_NAME,
            test_refresh_token=graph_service.test_refresh_token_with_rotation,
        )

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@login_required
def api_retry_refresh_account(account_id: int) -> Any:
    """重试单个失败账号的刷新"""
    return api_refresh_account(account_id)

@login_required
def api_refresh_failed_accounts() -> Any:
    """重试所有失败的账号"""
    db = get_db()
    trace_id_value = None
    try:
        trace_id_value = getattr(g, "trace_id", None)
    except Exception:
        trace_id_value = None
    requested_by_ip = get_client_ip()
    requested_by_user_agent = get_user_agent()

    response_data, status_code = refresh_service.refresh_failed_accounts(
        db=db,
        trace_id=trace_id_value,
        requested_by_ip=requested_by_ip,
        requested_by_user_agent=requested_by_user_agent,
        lock_name=REFRESH_LOCK_NAME,
        test_refresh_token=graph_service.test_refresh_token_with_rotation,
    )
    return jsonify(response_data), status_code

@login_required
def api_trigger_scheduled_refresh() -> Any:
    """手动触发定时刷新（支持强制刷新）"""
    force = request.args.get("force", "false").lower() == "true"
    trace_id_value = None
    try:
        trace_id_value = getattr(g, "trace_id", None)
    except Exception:
        trace_id_value = None
    requested_by_ip = get_client_ip()
    requested_by_user_agent = get_user_agent()

    # 获取配置
    refresh_interval_days = int(settings_repo.get_setting("refresh_interval_days", "30"))
    use_cron = settings_repo.get_setting("use_cron_schedule", "false").lower() == "true"

    # 执行刷新（使用流式响应）
    def generate():
        yield from refresh_service.stream_trigger_scheduled_refresh(
            force=force,
            refresh_interval_days=refresh_interval_days,
            use_cron=use_cron,
            trace_id=trace_id_value,
            requested_by_ip=requested_by_ip,
            requested_by_user_agent=requested_by_user_agent,
            lock_name=REFRESH_LOCK_NAME,
            test_refresh_token=graph_service.test_refresh_token_with_rotation,
        )

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 刷新日志 API ====================

@login_required
def api_get_refresh_logs() -> Any:
    """获取所有账号的刷新历史（近半年）"""
    db = get_db()
    limit = int(request.args.get("limit", 1000))
    offset = int(request.args.get("offset", 0))

    cursor = db.execute(
        """
        SELECT l.*, a.email as account_email
        FROM account_refresh_logs l
        LEFT JOIN accounts a ON l.account_id = a.id
        WHERE l.refresh_type IN ('manual', 'manual_all', 'scheduled', 'retry')
        AND l.created_at >= datetime('now', '-6 months')
        ORDER BY l.created_at DESC
        LIMIT ? OFFSET ?
    """,
        (limit, offset),
    )

    logs = []
    for row in cursor.fetchall():
        logs.append(
            {
                "id": row["id"],
                "account_id": row["account_id"],
                "account_email": row["account_email"] or row["account_email"],
                "refresh_type": row["refresh_type"],
                "status": row["status"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
            }
        )

    return jsonify({"success": True, "logs": logs})

@login_required
def api_get_account_refresh_logs(account_id: int) -> Any:
    """获取单个账号的刷新历史"""
    db = get_db()
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    cursor = db.execute(
        """
        SELECT * FROM account_refresh_logs
        WHERE account_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """,
        (account_id, limit, offset),
    )

    logs = []
    for row in cursor.fetchall():
        logs.append(
            {
                "id": row["id"],
                "account_id": row["account_id"],
                "account_email": row["account_email"],
                "refresh_type": row["refresh_type"],
                "status": row["status"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
            }
        )

    return jsonify({"success": True, "logs": logs})

@login_required
def api_get_failed_refresh_logs() -> Any:
    """获取所有失败的刷新记录"""
    db = get_db()

    # 获取每个账号最近一次失败的刷新记录
    cursor = db.execute("""
        SELECT l.*, a.email as account_email, a.status as account_status
        FROM account_refresh_logs l
        INNER JOIN (
            SELECT account_id, MAX(created_at) as last_refresh
            FROM account_refresh_logs
            GROUP BY account_id
        ) latest ON l.account_id = latest.account_id AND l.created_at = latest.last_refresh
        LEFT JOIN accounts a ON l.account_id = a.id
        WHERE l.status = 'failed'
        ORDER BY l.created_at DESC
    """)

    logs = []
    for row in cursor.fetchall():
        logs.append(
            {
                "id": row["id"],
                "account_id": row["account_id"],
                "account_email": row["account_email"] or row["account_email"],
                "account_status": row["account_status"],
                "refresh_type": row["refresh_type"],
                "status": row["status"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
            }
        )

    return jsonify({"success": True, "logs": logs})

@login_required
def api_get_invalid_token_candidates() -> Any:
    """获取最近一次刷新失败且命中 invalid token 判定的候选账号列表。"""
    db = get_db()
    limit = request.args.get("limit", default=200, type=int)
    offset = request.args.get("offset", default=0, type=int)

    if limit is None:
        limit = 200
    if offset is None:
        offset = 0
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    rows = db.execute(
        """
        SELECT
            l.id as refresh_log_id,
            l.account_id,
            COALESCE(a.email, l.account_email) as account_email,
            a.status as account_status,
            l.refresh_type,
            l.error_message,
            l.created_at
        FROM account_refresh_logs l
        INNER JOIN (
            SELECT account_id, MAX(id) AS max_id
            FROM account_refresh_logs
            GROUP BY account_id
        ) latest
            ON l.account_id = latest.account_id
            AND l.id = latest.max_id
        LEFT JOIN accounts a
            ON a.id = l.account_id
        WHERE l.status = 'failed'
          AND (
              LOWER(COALESCE(l.error_message, '')) LIKE '%invalid_grant%'
              OR LOWER(COALESCE(l.error_message, '')) LIKE '%aadsts70000%'
          )
        ORDER BY l.id DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()

    candidates = []
    for row in rows:
        classified = refresh_service._classify_refresh_failure(row["error_message"])
        if not classified.get("is_invalid_token"):
            continue

        candidates.append(
            {
                "refresh_log_id": row["refresh_log_id"],
                "account_id": row["account_id"],
                "account_email": row["account_email"],
                "account_status": row["account_status"],
                "refresh_type": row["refresh_type"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
                "reason_code": classified.get("reason_code"),
                "reason_label": classified.get("reason_label"),
                "is_invalid_token": True,
            }
        )

    return jsonify(
        {
            "success": True,
            "candidates": candidates,
            "total": len(candidates),
            "limit": limit,
            "offset": offset,
        }
    )

@login_required
def api_get_refresh_stats() -> Any:
    """获取刷新统计信息（统计当前失败状态的邮箱数量）"""
    db = get_db()

    cursor = db.execute("""
        SELECT MAX(created_at) as last_refresh_time
        FROM account_refresh_logs
        WHERE refresh_type IN ('manual', 'manual_all', 'scheduled', 'retry')
    """)
    row = cursor.fetchone()
    last_refresh_time = row["last_refresh_time"] if row else None

    cursor = db.execute("""
        SELECT COUNT(*) as total_accounts
        FROM accounts
        WHERE status = 'active'
    """)
    total_accounts = cursor.fetchone()["total_accounts"]

    cursor = db.execute("""
        SELECT COUNT(DISTINCT l.account_id) as failed_count
        FROM account_refresh_logs l
        INNER JOIN (
            SELECT account_id, MAX(created_at) as last_refresh
            FROM account_refresh_logs
            GROUP BY account_id
        ) latest ON l.account_id = latest.account_id AND l.created_at = latest.last_refresh
        INNER JOIN accounts a ON l.account_id = a.id
        WHERE l.status = 'failed' AND a.status = 'active'
    """)
    failed_count = cursor.fetchone()["failed_count"]

    return jsonify(
        {
            "success": True,
            "stats": {
                "total": total_accounts,
                "success_count": total_accounts - failed_count,
                "failed_count": failed_count,
                "last_refresh_time": last_refresh_time,
            },
        }
    )


# ==================== 通知参与 API（兼容旧 Telegram 路径） ====================

@login_required
def api_refresh_selected_accounts() -> Any:
    """刷新指定账号列表的 token（SSE 流式响应）"""
    data = request.get_json(silent=True) or {}
    account_ids = data.get("account_ids", [])

    if not account_ids or not isinstance(account_ids, list):
        error_payload = build_error_payload(
            "INVALID_PARAMS",
            "account_ids 不能为空",
            "ValidationError",
            400,
            "account_ids must be a non-empty list of integers",
        )
        return jsonify({"success": False, "error": error_payload}), 400

    # 确保所有 ID 为整数
    try:
        account_ids = [int(aid) for aid in account_ids]
    except (TypeError, ValueError):
        error_payload = build_error_payload(
            "INVALID_PARAMS",
            "account_ids 必须为整数列表",
            "ValidationError",
            400,
            "account_ids must be a list of integers",
        )
        return jsonify({"success": False, "error": error_payload}), 400

    trace_id_value = None
    try:
        trace_id_value = getattr(g, "trace_id", None)
    except Exception:
        trace_id_value = None
    requested_by_ip = get_client_ip()
    requested_by_user_agent = get_user_agent()

    def generate():
        yield from refresh_service.stream_refresh_selected_accounts(
            account_ids=account_ids,
            trace_id=trace_id_value,
            requested_by_ip=requested_by_ip,
            requested_by_user_agent=requested_by_user_agent,
            lock_name=REFRESH_LOCK_NAME,
            test_refresh_token=graph_service.test_refresh_token_with_rotation,
        )

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
