from __future__ import annotations

import json
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from outlook_web.db import create_sqlite_connection
from outlook_web.errors import build_error_payload, generate_trace_id
from outlook_web.repositories.distributed_locks import (
    acquire_distributed_lock,
    release_distributed_lock,
)
from outlook_web.repositories.refresh_runs import create_refresh_run, finish_refresh_run
from outlook_web.security.crypto import decrypt_data, encrypt_data

from .classify import _record_invalid_token_failure, compute_refresh_lock_ttl_seconds
from .constants import build_refreshable_outlook_account_where

def refresh_failed_accounts(
    *,
    db,
    trace_id: Optional[str],
    requested_by_ip: str,
    requested_by_user_agent: str,
    lock_name: str,
    test_refresh_token: Callable[[str, str, Optional[str]], Tuple[bool, Optional[str], Optional[str]]],
) -> Tuple[Dict[str, Any], int]:
    """重试所有失败的账号（非流式）"""
    lock_owner_id = uuid.uuid4().hex

    cursor = db.execute(f"""
        SELECT DISTINCT a.id, a.email, a.client_id, a.refresh_token, a.group_id
        FROM accounts a
        INNER JOIN (
            SELECT account_id, MAX(created_at) as last_refresh
            FROM account_refresh_logs
            GROUP BY account_id
        ) latest ON a.id = latest.account_id
        INNER JOIN account_refresh_logs l ON a.id = l.account_id AND l.created_at = latest.last_refresh
        WHERE l.status = 'failed'
          AND a.status = 'active'
          AND {build_refreshable_outlook_account_where("a.account_type", "a.provider")}
    """)
    accounts = cursor.fetchall()

    total = len(accounts)
    run_id = create_refresh_run(
        db,
        trigger_source="retry_failed",
        trace_id=trace_id or generate_trace_id(),
        requested_by_ip=requested_by_ip,
        requested_by_user_agent=requested_by_user_agent,
        total=total,
    )

    ttl_seconds = compute_refresh_lock_ttl_seconds(total, 0)
    ok, lock_info = acquire_distributed_lock(db, lock_name, lock_owner_id, ttl_seconds)
    if not ok:
        finish_refresh_run(db, run_id, "skipped", total, 0, 0, "刷新任务冲突：已有刷新在执行")
        error_payload = build_error_payload(
            code="REFRESH_CONFLICT",
            message="当前已有刷新任务执行中，请等待当前任务完成后再重试",
            err_type="ConflictError",
            status=409,
            details=lock_info or "",
            trace_id=trace_id,
            message_en="Another refresh task is already running. Wait for it to finish and retry.",
        )
        return {"success": False, "error": error_payload}, 409

    success_count = 0
    failed_count = 0
    failed_list: List[Dict[str, Any]] = []
    invalid_token_failed_count = 0
    invalid_token_failed_list: List[Dict[str, Any]] = []

    try:
        for account in accounts:
            account_id = account["id"]
            account_email = account["email"]
            client_id = account["client_id"]
            encrypted_refresh_token = account["refresh_token"]

            proxy_url = ""
            group_id = account["group_id"]
            if group_id:
                try:
                    group_row = db.execute("SELECT proxy_url FROM groups WHERE id = ?", (group_id,)).fetchone()
                    if group_row:
                        proxy_url = group_row["proxy_url"] or ""
                except Exception:
                    proxy_url = ""

            try:
                refresh_token = decrypt_data(encrypted_refresh_token) if encrypted_refresh_token else encrypted_refresh_token
            except Exception as e:
                failed_count += 1
                error_msg = f"解密 token 失败: {str(e)}"
                failed_list.append({"id": account_id, "email": account_email, "error": error_msg})
                if _record_invalid_token_failure(
                    invalid_token_failed_list=invalid_token_failed_list,
                    account_id=account_id,
                    account_email=account_email,
                    error_message=error_msg,
                ):
                    invalid_token_failed_count += 1
                try:
                    from outlook_web.repositories.refresh_logs import log_refresh_result

                    log_refresh_result(
                        account_id,
                        account_email,
                        "retry",
                        "failed",
                        error_msg,
                        run_id=run_id,
                    )
                except Exception:
                    pass
                continue

            success, error_msg, new_refresh_token = test_refresh_token(client_id, refresh_token, proxy_url)
            try:
                from outlook_web.repositories.refresh_logs import log_refresh_result

                log_refresh_result(
                    account_id,
                    account_email,
                    "retry",
                    "success" if success else "failed",
                    error_msg,
                    run_id=run_id,
                )
            except Exception:
                pass

            if success:
                try:
                    if isinstance(new_refresh_token, str) and new_refresh_token.strip() and new_refresh_token != refresh_token:
                        db.execute(
                            """
                            UPDATE accounts
                            SET refresh_token = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """,
                            (encrypt_data(new_refresh_token), account_id),
                        )
                    db.execute(
                        """
                        UPDATE accounts
                        SET last_refresh_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (account_id,),
                    )
                    db.commit()
                except Exception:
                    pass
                success_count += 1
            else:
                failed_count += 1
                failed_list.append({"id": account_id, "email": account_email, "error": error_msg})
                if _record_invalid_token_failure(
                    invalid_token_failed_list=invalid_token_failed_list,
                    account_id=account_id,
                    account_email=account_email,
                    error_message=error_msg,
                ):
                    invalid_token_failed_count += 1
    finally:
        release_distributed_lock(db, lock_name, lock_owner_id)

    finish_refresh_run(
        db,
        run_id,
        "completed",
        total,
        success_count,
        failed_count,
        f"完成：成功 {success_count}，失败 {failed_count}",
    )

    return (
        {
            "success": True,
            "run_id": run_id,
            "total": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_list": failed_list,
            "invalid_token_failed_count": invalid_token_failed_count,
            "invalid_token_failed_list": invalid_token_failed_list,
        },
        200,
    )
