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

from .constants import INVALID_TOKEN_ERROR_KEYWORDS, INVALID_TOKEN_FAILED_LIST_LIMIT, REFRESH_LOCK_TTL_SECONDS


def _classify_refresh_failure(error_message: Optional[str]) -> Dict[str, Any]:
    """统一判定刷新失败是否属于失效 token（方案 C 首版口径）。"""
    normalized = str(error_message or "").strip().lower()
    is_invalid_token = any(keyword in normalized for keyword in INVALID_TOKEN_ERROR_KEYWORDS)
    if not is_invalid_token:
        return {
            "is_invalid_token": False,
            "reason_code": None,
            "reason_label": None,
        }

    return {
        "is_invalid_token": True,
        "reason_code": "INVALID_GRANT_OR_AADSTS70000",
        "reason_label": "refresh_token_invalid_or_expired",
    }


def _record_invalid_token_failure(
    *,
    invalid_token_failed_list: List[Dict[str, Any]],
    account_id: int,
    account_email: str,
    error_message: Optional[str],
) -> bool:
    classified = _classify_refresh_failure(error_message)
    if not classified.get("is_invalid_token"):
        return False

    if len(invalid_token_failed_list) < INVALID_TOKEN_FAILED_LIST_LIMIT:
        invalid_token_failed_list.append(
            {
                "id": account_id,
                "email": account_email,
                "error": error_message,
                "reason_code": classified.get("reason_code"),
                "reason_label": classified.get("reason_label"),
            }
        )
    return True


def utcnow() -> datetime:
    """返回 naive UTC 时间（等价于旧的 datetime.utcnow()）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_refresh_lock_ttl_seconds(total: int, delay_seconds: int) -> int:
    try:
        total = int(total or 0)
    except Exception:
        total = 0
    try:
        delay_seconds = int(delay_seconds or 0)
    except Exception:
        delay_seconds = 0

    estimated = int(total * (max(delay_seconds, 0) + 2) + 600)
    ttl = max(REFRESH_LOCK_TTL_SECONDS, estimated)
    return min(ttl, 60 * 60 * 24)  # 最大 24 小时
