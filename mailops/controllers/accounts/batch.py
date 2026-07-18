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

from .helpers import _normalize_account_status


@login_required
def api_batch_update_status() -> Any:
    """批量更新账号状态（用于失效账号治理主动作）。"""
    data = request.get_json(silent=True) or {}
    account_ids = data.get("account_ids", [])
    normalized_status = _normalize_account_status(data.get("status"))

    if not isinstance(account_ids, list) or not account_ids:
        return build_error_response(
            "ACCOUNT_IDS_REQUIRED",
            "请选择要修改状态的账号",
            message_en="Please select accounts to update status",
        )

    if not normalized_status:
        return build_error_response(
            "INVALID_PARAM",
            "状态值无效",
            message_en="Invalid account status",
            status=400,
        )

    try:
        parsed_ids = [int(aid) for aid in account_ids]
    except (TypeError, ValueError):
        return build_error_response(
            "INVALID_PARAM",
            "account_ids 必须为整数列表",
            message_en="account_ids must be a list of integers",
            status=400,
        )

    deduped_ids: List[int] = []
    seen_ids = set()
    for aid in parsed_ids:
        if aid in seen_ids:
            continue
        seen_ids.add(aid)
        deduped_ids.append(aid)

    db = get_db()
    placeholders = ",".join("?" * len(deduped_ids))
    try:
        existing_rows = db.execute(
            f"SELECT id FROM accounts WHERE id IN ({placeholders})",
            deduped_ids,
        ).fetchall()
        existing_ids = {int(row["id"]) for row in existing_rows}

        missing_ids = [aid for aid in deduped_ids if aid not in existing_ids]
        if existing_ids:
            existing_id_list = sorted(existing_ids)
            update_placeholders = ",".join("?" * len(existing_id_list))
            db.execute(
                f"""
                UPDATE accounts
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({update_placeholders})
                """,
                [normalized_status] + existing_id_list,
            )
            db.commit()

        updated_count = len(existing_ids)
        failed_count = len(missing_ids)
        log_audit(
            "update",
            "account_status",
            None,
            f"批量更新账号状态：status={normalized_status}，成功={updated_count}，失败={failed_count}",
        )
        return jsonify(
            {
                "success": True,
                "message": f"成功更新 {updated_count} 个账号状态" + (f"，失败 {failed_count} 个" if failed_count > 0 else ""),
                "status": normalized_status,
                "updated_count": updated_count,
                "failed_count": failed_count,
                "missing_ids": missing_ids,
            }
        )
    except Exception as e:
        return build_error_response(
            "ACCOUNT_STATUS_BATCH_UPDATE_FAILED",
            "批量更新账号状态失败",
            message_en="Failed to batch update account status",
            status=500,
            details=str(e),
        )


@login_required
def api_batch_notification_toggle() -> Any:
    """批量切换账号通知参与开关。"""
    data = request.get_json(silent=True) or {}
    account_ids = data.get("account_ids", [])
    enabled = bool(data.get("enabled", False))

    if not isinstance(account_ids, list) or not account_ids:
        return build_error_response(
            "ACCOUNT_IDS_REQUIRED",
            "请选择要操作通知的账号",
            message_en="Please select accounts for notification toggle",
        )

    try:
        parsed_ids = [int(aid) for aid in account_ids]
    except (TypeError, ValueError):
        return build_error_response(
            "INVALID_PARAM",
            "account_ids 必须为整数列表",
            message_en="account_ids must be a list of integers",
            status=400,
        )

    deduped_ids: List[int] = []
    seen_ids = set()
    for aid in parsed_ids:
        if aid in seen_ids:
            continue
        seen_ids.add(aid)
        deduped_ids.append(aid)

    updated_count = 0
    failed_count = 0
    missing_ids: List[int] = []

    for aid in deduped_ids:
        success = accounts_repo.toggle_telegram_push(aid, enabled)
        if success:
            updated_count += 1
        else:
            failed_count += 1
            missing_ids.append(aid)

    action = "开启" if enabled else "关闭"
    log_audit(
        "batch_notification_toggle",
        "account",
        None,
        f"批量{action}通知：成功={updated_count}，失败={failed_count}",
    )

    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "missing_ids": missing_ids,
            "message": f"成功{action} {updated_count} 个账号通知" + (f"，{failed_count} 个失败" if failed_count else ""),
        }
    )


@login_required
def api_batch_delete_accounts() -> Any:
    """
    批量删除账号 API

    功能：支持一次性删除多个账号，记录审计日志
    """
    data = request.get_json()
    account_ids = data.get("account_ids", [])

    if not account_ids:
        return build_error_response(
            "ACCOUNT_IDS_REQUIRED",
            "请选择要删除的账号",
            message_en="Please select the accounts to delete",
        )

    if not isinstance(account_ids, list):
        return build_error_response("INVALID_PARAM", "参数格式错误", message_en="Invalid request parameters")

    deleted_count = 0
    failed_count = 0

    for account_id in account_ids:
        try:
            # 获取邮箱地址和 provider 用于审计日志和保护判断
            db = get_db()
            row = db.execute("SELECT email, provider FROM accounts WHERE id = ?", (account_id,)).fetchone()
            email_addr = row["email"] if row else ""

            # 邮箱池管理的 CF 临时邮箱不允许手动删除，跳过
            if row and (row["provider"] or "").lower() == "cloudflare_temp_mail":
                failed_count += 1
                continue

            if accounts_repo.delete_account_by_id(account_id):
                log_audit(
                    "delete",
                    "account",
                    str(account_id),
                    f"批量删除账号：{email_addr}" if email_addr else "批量删除账号",
                )
                deleted_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1

    return jsonify(
        {
            "success": True,
            "message": f"成功删除 {deleted_count} 个账号" + (f"，失败 {failed_count} 个" if failed_count > 0 else ""),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
        }
    )


# ==================== 批量操作 API ====================


@login_required
def api_batch_manage_tags() -> Any:
    """批量管理账号标签"""
    data = request.json
    account_ids: List[int] = data.get("account_ids", [])
    tag_id = data.get("tag_id")
    action = data.get("action")  # add, remove

    if not account_ids or not tag_id or not action:
        return build_error_response("INVALID_PARAM", "参数不完整", message_en="Missing required parameters")

    count = 0
    for acc_id in account_ids:
        if action == "add":
            if tags_repo.add_account_tag(acc_id, tag_id):
                count += 1
        elif action == "remove":
            if tags_repo.remove_account_tag(acc_id, tag_id):
                count += 1

    try:
        details = json.dumps(
            {
                "action": action,
                "tag_id": tag_id,
                "accounts": len(account_ids),
                "affected": count,
            },
            ensure_ascii=False,
        )
    except Exception:
        details = f"action={action} tag_id={tag_id} accounts={len(account_ids)} affected={count}"
    log_audit("update", "account_tags", str(tag_id), details)
    return jsonify({"success": True, "message": f"成功处理 {count} 个账号"})


@login_required
def api_batch_update_account_group() -> Any:
    """批量更新账号分组"""
    data = request.json
    account_ids = data.get("account_ids", [])
    group_id = data.get("group_id")

    if not account_ids:
        return build_error_response(
            "ACCOUNT_IDS_REQUIRED",
            "请选择要修改的账号",
            message_en="Please select the accounts to update",
        )

    if not group_id:
        return build_error_response(
            "GROUP_ID_REQUIRED",
            "请选择目标分组",
            message_en="Please select a target group",
        )

    # 验证分组存在
    group = groups_repo.get_group_by_id(group_id)
    if not group:
        return build_error_response(
            "GROUP_NOT_FOUND",
            "目标分组不存在",
            message_en="Target group not found",
            status=404,
        )

    # 检查是否是临时邮箱分组（系统保留分组）
    if group.get("is_system"):
        return build_error_response(
            "SYSTEM_GROUP_PROTECTED",
            "不能移动到系统分组",
            message_en="Cannot move accounts into a system group",
            status=403,
        )

    # 批量更新
    db = get_db()
    try:
        placeholders = ",".join("?" * len(account_ids))
        db.execute(
            f"""
            UPDATE accounts SET group_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """,
            [group_id] + account_ids,
        )
        db.commit()
        log_audit(
            "update",
            "account_group",
            str(group_id),
            f"批量移动分组：账号数={len(account_ids)}",
        )
        return jsonify(
            {
                "success": True,
                "message": f"已将 {len(account_ids)} 个账号移动到「{group['name']}」分组",
            }
        )
    except Exception as e:
        return build_error_response(
            "ACCOUNT_GROUP_BATCH_UPDATE_FAILED",
            "批量移动分组失败",
            message_en="Failed to move accounts to the target group",
            status=500,
            details=str(e),
        )
