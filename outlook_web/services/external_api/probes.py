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

from .access import _can_check_external_access, ensure_external_email_access, get_current_external_api_consumer
from .constants import MAX_TIMEOUT_SECONDS
from .errors import ExternalApiError, InvalidParamError, MailNotFoundError
from .messages import get_latest_message_for_external

# Outlook IMAP 回退服务器（保持与内部接口一致）

def wait_for_message(  # noqa: C901
    *,
    email_addr: str,
    timeout_seconds: int = 30,
    poll_interval: int = 5,
    folder: str = "inbox",
    from_contains: str = "",
    subject_contains: str = "",
    since_minutes: Optional[int] = None,
    baseline_timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        timeout_seconds = int(timeout_seconds)
        poll_interval = int(poll_interval)
    except Exception as exc:
        raise InvalidParamError("timeout_seconds/poll_interval 参数无效") from exc

    if timeout_seconds <= 0 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise InvalidParamError(f"timeout_seconds 必须在 1-{MAX_TIMEOUT_SECONDS} 秒之间")
    if poll_interval <= 0 or poll_interval > timeout_seconds:
        raise InvalidParamError("poll_interval 参数无效")

    # 记录进入等待接口时的时间戳，避免把请求开始前已存在的旧邮件误判成"新到达"。
    # 如果调用方已通过 claim_token 传入 baseline_timestamp，优先使用（更早的基准）。
    if _can_check_external_access():
        ensure_external_email_access(email_addr)
    if baseline_timestamp is None or baseline_timestamp <= 0:
        baseline_timestamp = int(time.time())
    start = time.time()
    last_error: Optional[ExternalApiError] = None
    while True:
        try:
            if _can_check_external_access():
                ensure_external_email_access(email_addr)
            latest_message = get_latest_message_for_external(
                email_addr=email_addr,
                folder=folder,
                from_contains=from_contains,
                subject_contains=subject_contains,
                since_minutes=since_minutes,
                baseline_timestamp=baseline_timestamp,
            )
            if int(latest_message.get("timestamp") or 0) >= baseline_timestamp:
                return latest_message
        except MailNotFoundError as exc:
            last_error = exc

        if time.time() - start >= timeout_seconds:
            raise MailNotFoundError("等待超时，未检测到匹配邮件", data={"email": email_addr}) from last_error

        time.sleep(poll_interval)


# ── P2: 异步探测 (probe) ──────────────────────────────

def _validate_probe_params(
    email_addr: str,
    timeout_seconds: int,
    poll_interval: int,
) -> None:
    """校验探测参数，与 wait_for_message 保持一致。"""
    if not email_addr:
        raise InvalidParamError("email 参数不能为空")
    try:
        timeout_seconds = int(timeout_seconds)
        poll_interval = int(poll_interval)
    except Exception as exc:
        raise InvalidParamError("timeout_seconds/poll_interval 参数无效") from exc
    if timeout_seconds <= 0 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise InvalidParamError(f"timeout_seconds 必须在 1-{MAX_TIMEOUT_SECONDS} 秒之间")
    if poll_interval <= 0 or poll_interval > timeout_seconds:
        raise InvalidParamError("poll_interval 参数无效")

def create_probe(
    *,
    email_addr: str,
    timeout_seconds: int = 30,
    poll_interval: int = 5,
    folder: str = "inbox",
    from_contains: str = "",
    subject_contains: str = "",
    since_minutes: Optional[int] = None,
    baseline_timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    """
    创建一个异步探测请求，后台 worker 会定期轮询直到匹配或超时。
    返回 probe_id 供后续查询。
    """
    import uuid

    from outlook_web.db import get_db

    _validate_probe_params(email_addr, timeout_seconds, poll_interval)

    mailbox = mailbox_resolver.resolve_mailbox(email_addr)
    mailbox_resolver.ensure_mailbox_can_read(mailbox, consumer=get_current_external_api_consumer())

    probe_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=int(timeout_seconds))

    # PR#27：若传入了 baseline_timestamp，使用它；否则使用 now 作为基准
    effective_baseline = baseline_timestamp if (baseline_timestamp and baseline_timestamp > 0) else int(now.timestamp())

    db = get_db()
    db.execute(
        """
        INSERT INTO external_probe_cache
            (id, email_addr, folder, from_contains, subject_contains,
             since_minutes, timeout_seconds, poll_interval, status, expires_at, created_at, updated_at,
             baseline_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            probe_id,
            email_addr,
            folder,
            from_contains,
            subject_contains,
            since_minutes,
            int(timeout_seconds),
            int(poll_interval),
            expires_at.isoformat(),
            now.isoformat(),
            now.isoformat(),
            effective_baseline,
        ),
    )
    db.commit()

    return {
        "probe_id": probe_id,
        "status": "pending",
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "poll_url": f"/api/v1/external/probe/{probe_id}",
        "baseline_timestamp": effective_baseline,
    }

def get_probe_status(probe_id: str) -> Dict[str, Any]:
    """查询探测状态与结果。"""
    from outlook_web.db import get_db

    if not probe_id:
        raise InvalidParamError("probe_id 不能为空")

    db = get_db()
    row = db.execute("SELECT * FROM external_probe_cache WHERE id = ?", (probe_id,)).fetchone()

    if not row:
        raise MailNotFoundError("探测请求不存在", data={"probe_id": probe_id})

    result: Dict[str, Any] = {
        "probe_id": row["id"],
        "email": row["email_addr"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
    }

    if row["status"] == "matched" and row["result_json"]:
        try:
            result["message"] = json.loads(row["result_json"])
        except (json.JSONDecodeError, TypeError):
            result["message"] = None
    elif row["status"] == "timeout":
        result["error_code"] = "WAIT_TIMEOUT"
        result["error_message"] = row["error_message"] or "等待超时，未检测到匹配邮件"
    elif row["status"] == "error":
        result["error_code"] = row["error_code"] or "PROBE_ERROR"
        result["error_message"] = row["error_message"] or "探测过程中发生错误"
    elif row["status"] == "cancelled":
        result["error_code"] = row["error_code"] or "PROBE_CANCELLED"
        result["error_message"] = row["error_message"] or "探测因任务结束而被取消"

    return result

def cancel_pending_probes_for_email(
    email_addr: str,
    *,
    error_code: str = "PROBE_CANCELLED",
    error_message: str = "探测因任务结束而被取消",
) -> int:
    from outlook_web.db import get_db

    db = get_db()
    cursor = db.execute(
        """
        UPDATE external_probe_cache
        SET status = 'cancelled',
            error_code = ?,
            error_message = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE email_addr = ? AND status = 'pending'
        """,
        (error_code, error_message, email_addr),
    )
    db.commit()
    return cursor.rowcount

def _mark_expired_pending_probes(db: Any, now: str) -> None:
    db.execute(
        """
        UPDATE external_probe_cache
        SET status = 'timeout',
            error_message = '等待超时，未检测到匹配邮件',
            updated_at = ?
        WHERE status = 'pending' AND expires_at <= ?
        """,
        (now, now),
    )
    db.commit()

def _load_pending_probe_rows(db: Any, now: str, *, limit: int = 50) -> list[Any]:
    return db.execute(
        """
        SELECT * FROM external_probe_cache
        WHERE status = 'pending' AND expires_at > ?
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (now, limit),
    ).fetchall()

def _get_probe_baseline_timestamp(row: Any) -> int:
    # PR#27：若 probe 创建时传入了 baseline_timestamp（来自 claim_token），优先使用
    try:
        stored = row["baseline_timestamp"]
        if stored is not None and int(stored) > 0:
            return int(stored)
    except (TypeError, KeyError, ValueError):
        pass
    # 回退：从 created_at 推算
    try:
        created_str = row["created_at"] or ""
        if created_str.endswith("Z"):
            created_str = created_str[:-1] + "+00:00"
        created_dt = datetime.fromisoformat(created_str)
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        return int(created_dt.timestamp())
    except Exception:
        return int(time.time()) - int(row["timeout_seconds"] or 0)

def _mark_probe_matched(db: Any, probe_id: str, latest: Dict[str, Any], now: str) -> None:
    db.execute(
        """
        UPDATE external_probe_cache
        SET status = 'matched', result_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (json.dumps(latest, ensure_ascii=False), now, probe_id),
    )
    db.commit()

def _mark_probe_error(db: Any, probe_id: str, exc: Exception, now: str) -> None:
    db.execute(
        """
        UPDATE external_probe_cache
        SET status = 'error', error_code = 'PROBE_ERROR',
            error_message = ?, updated_at = ?
        WHERE id = ?
        """,
        (str(exc)[:500], now, probe_id),
    )
    db.commit()

def _poll_single_probe(db: Any, row: Any, now: str) -> None:
    latest = get_latest_message_for_external(
        email_addr=row["email_addr"],
        folder=row["folder"],
        from_contains=row["from_contains"],
        subject_contains=row["subject_contains"],
        since_minutes=row["since_minutes"],
    )
    if int(latest.get("timestamp") or 0) >= _get_probe_baseline_timestamp(row):
        _mark_probe_matched(db, row["id"], latest, now)

def poll_pending_probes(app: Any = None) -> int:
    """
    后台任务：遍历所有 pending 状态的探测请求，执行一轮轮询。
    返回本轮处理的探测数量。
    """
    from outlook_web.db import get_db

    ctx = None
    if app is not None:
        ctx = app.app_context()
        ctx.push()

    try:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        _mark_expired_pending_probes(db, now)
        rows = _load_pending_probe_rows(db, now)

        processed = 0
        for row in rows:
            processed += 1
            try:
                _poll_single_probe(db, row, now)
            except MailNotFoundError:
                continue
            except Exception as exc:
                _mark_probe_error(db, row["id"], exc, now)

        return processed
    finally:
        if ctx is not None:
            ctx.pop()

def cleanup_expired_probes(app: Any = None, max_age_minutes: int = 30) -> int:
    """清理已完成/超时/错误的探测记录（默认清理 30 分钟前的）。"""
    from outlook_web.db import get_db

    ctx = None
    if app is not None:
        ctx = app.app_context()
        ctx.push()

    try:
        db = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()
        cursor = db.execute(
            """
            DELETE FROM external_probe_cache
            WHERE status IN ('matched', 'timeout', 'error') AND updated_at < ?
            """,
            (cutoff,),
        )
        db.commit()
        return cursor.rowcount
    finally:
        if ctx is not None:
            ctx.pop()
