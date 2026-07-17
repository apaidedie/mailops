from __future__ import annotations

import json
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from outlook_web.db import create_sqlite_connection
from outlook_web.errors import build_error_payload, generate_trace_id
from outlook_web.repositories import distributed_locks
from outlook_web.repositories.refresh_runs import create_refresh_run, finish_refresh_run
from outlook_web.security.crypto import decrypt_data, encrypt_data

from .classify import _record_invalid_token_failure, compute_refresh_lock_ttl_seconds
from .constants import is_refreshable_outlook_account


def stream_refresh_selected_accounts(
    *,
    account_ids: List[int],
    trace_id: Optional[str],
    requested_by_ip: str,
    requested_by_user_agent: str,
    lock_name: str,
    test_refresh_token: Callable[[str, str, Optional[str]], Tuple[bool, Optional[str], Optional[str]]],
) -> Iterator[str]:
    """刷新指定账号列表的 token（SSE 流式输出）"""
    conn = create_sqlite_connection()
    lock_owner_id = uuid.uuid4().hex
    lock_acquired = False
    run_id = None

    try:
        delay_row = conn.execute("SELECT value FROM settings WHERE key = 'refresh_delay_seconds'").fetchone()
        delay_seconds = int(delay_row["value"]) if delay_row else 5

        try:
            conn.execute("DELETE FROM account_refresh_logs WHERE created_at < datetime('now', '-6 months')")
            conn.execute("DELETE FROM refresh_runs WHERE started_at < datetime('now', '-6 months')")
            conn.execute("DELETE FROM distributed_locks WHERE expires_at < ?", (time.time(),))
            conn.commit()
        except Exception:
            pass

        # 查询指定 ID 的账号，过滤出 Outlook 类型（IMAP 账号跳过）
        placeholders = ",".join("?" * len(account_ids))
        all_rows = conn.execute(
            f"""
            SELECT id, email, client_id, refresh_token, group_id, account_type, provider
            FROM accounts
            WHERE id IN ({placeholders})
              AND status = 'active'
            """,
            account_ids,
        ).fetchall()

        accounts = [row for row in all_rows if is_refreshable_outlook_account(row["account_type"], provider=row["provider"])]
        skipped_count = len(all_rows) - len(accounts)
        total = len(accounts)

        run_id = create_refresh_run(
            conn,
            trigger_source="manual_selected",
            trace_id=trace_id or generate_trace_id(),
            requested_by_ip=requested_by_ip,
            requested_by_user_agent=requested_by_user_agent,
            total=total,
        )

        ttl_seconds = compute_refresh_lock_ttl_seconds(total, delay_seconds)
        ok, lock_info = distributed_locks.acquire_distributed_lock(conn, lock_name, lock_owner_id, ttl_seconds)
        if not ok:
            finish_refresh_run(conn, run_id, "skipped", total, 0, 0, "刷新任务冲突：已有刷新在执行")
            error_payload = build_error_payload(
                code="REFRESH_CONFLICT",
                message="当前已有刷新任务执行中，请等待当前任务完成后再重试",
                err_type="ConflictError",
                status=409,
                details=lock_info or "",
                trace_id=trace_id,
                message_en="Another refresh task is already running. Wait for it to finish and retry.",
            )
            yield f"data: {json.dumps({'type': 'error', 'error': error_payload}, ensure_ascii=False)}\n\n"
            return
        lock_acquired = True

        success_count = 0
        failed_count = 0
        failed_list: List[Dict[str, Any]] = []
        invalid_token_failed_count = 0
        invalid_token_failed_list: List[Dict[str, Any]] = []

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "start",
                    "total": total,
                    "skipped_count": skipped_count,
                    "delay_seconds": delay_seconds,
                    "run_id": run_id,
                    "trace_id": trace_id,
                    "refresh_type": "manual_selected",
                },
                ensure_ascii=False,
            )
            + "\n\n"
        )

        for index, account in enumerate(accounts, 1):
            account_id = account["id"]
            account_email = account["email"]
            client_id = account["client_id"]
            encrypted_refresh_token = account["refresh_token"]

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
                    conn.execute(
                        """
                        INSERT INTO account_refresh_logs (account_id, account_email, refresh_type, status, error_message, run_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            account_id,
                            account_email,
                            "manual_selected",
                            "failed",
                            error_msg,
                            run_id,
                        ),
                    )
                    conn.commit()
                except Exception:
                    pass
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "progress",
                            "current": index,
                            "total": total,
                            "email": account_email,
                            "account_id": account_id,
                            "result": "failed",
                            "error_message": error_msg,
                            "last_refresh_at": None,
                            "success_count": success_count,
                            "failed_count": failed_count,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
                continue

            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "progress",
                        "current": index,
                        "total": total,
                        "email": account_email,
                        "account_id": account_id,
                        "result": "processing",
                        "error_message": None,
                        "last_refresh_at": None,
                        "success_count": success_count,
                        "failed_count": failed_count,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            proxy_url = ""
            group_id = account["group_id"]
            if group_id:
                try:
                    group_row = conn.execute("SELECT proxy_url FROM groups WHERE id = ?", (group_id,)).fetchone()
                    if group_row:
                        proxy_url = group_row["proxy_url"] or ""
                except Exception:
                    proxy_url = ""

            success, error_msg, new_refresh_token = test_refresh_token(client_id, refresh_token, proxy_url)

            last_refresh_at = None
            try:
                conn.execute(
                    """
                    INSERT INTO account_refresh_logs (account_id, account_email, refresh_type, status, error_message, run_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        account_id,
                        account_email,
                        "manual_selected",
                        "success" if success else "failed",
                        error_msg,
                        run_id,
                    ),
                )

                if success:
                    if isinstance(new_refresh_token, str) and new_refresh_token.strip() and new_refresh_token != refresh_token:
                        conn.execute(
                            """
                            UPDATE accounts
                            SET refresh_token = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """,
                            (encrypt_data(new_refresh_token), account_id),
                        )
                    conn.execute(
                        """
                        UPDATE accounts
                        SET last_refresh_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (account_id,),
                    )
                    # 取最新的 last_refresh_at 用于返回给前端
                    row = conn.execute(
                        "SELECT last_refresh_at FROM accounts WHERE id = ?",
                        (account_id,),
                    ).fetchone()
                    if row:
                        last_refresh_at = row["last_refresh_at"]
                conn.commit()
            except Exception:
                pass

            if success:
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

            # 发送带 account_id 和 result 的完整 progress 事件
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "progress",
                        "current": index,
                        "total": total,
                        "email": account_email,
                        "account_id": account_id,
                        "result": "success" if success else "failed",
                        "error_message": error_msg if not success else None,
                        "last_refresh_at": last_refresh_at,
                        "success_count": success_count,
                        "failed_count": failed_count,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            if index < total and delay_seconds > 0:
                jitter = random.uniform(0, 2)
                wait_seconds = delay_seconds + jitter
                yield f"data: {json.dumps({'type': 'delay', 'seconds': wait_seconds}, ensure_ascii=False)}\n\n"
                time.sleep(wait_seconds)

        finish_refresh_run(
            conn,
            run_id,
            "completed",
            total,
            success_count,
            failed_count,
            f"完成：成功 {success_count}，失败 {failed_count}",
        )

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "complete",
                    "total": total,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "failed_list": failed_list,
                    "invalid_token_failed_count": invalid_token_failed_count,
                    "invalid_token_failed_list": invalid_token_failed_list,
                    "run_id": run_id,
                },
                ensure_ascii=False,
            )
            + "\n\n"
        )
    except Exception as e:
        try:
            if run_id:
                finish_refresh_run(conn, run_id, "failed", 0, 0, 0, str(e))
        except Exception:
            pass
        error_payload = build_error_payload(
            code="REFRESH_FAILED",
            message="刷新执行失败",
            err_type="RefreshError",
            status=500,
            details=str(e),
            trace_id=trace_id,
        )
        yield f"data: {json.dumps({'type': 'error', 'error': error_payload}, ensure_ascii=False)}\n\n"
    finally:
        if lock_acquired:
            distributed_locks.release_distributed_lock(conn, lock_name, lock_owner_id)
        try:
            conn.close()
        except Exception:
            pass
