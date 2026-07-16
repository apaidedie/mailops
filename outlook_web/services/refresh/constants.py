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

REFRESH_LOCK_TTL_SECONDS = 60 * 60 * 2  # 2 小时，避免异常中断导致长时间卡死


def build_refreshable_outlook_account_where(
    column: str = "account_type",
    provider_column: str = "provider",
) -> str:
    """构造 Outlook-only 刷新规则，兼容历史空 account_type 数据。
    排除 provider=cloudflare_temp_mail（CF pool 账号无 OAuth token，不应进入刷新链路）。"""
    return f"({column} = 'outlook' OR {column} IS NULL) AND ({provider_column} != 'cloudflare_temp_mail' OR {provider_column} IS NULL)"


REFRESHABLE_OUTLOOK_ACCOUNT_WHERE = build_refreshable_outlook_account_where()

REFRESHABLE_OUTLOOK_ACCOUNT_SELECT = f"""
    SELECT id, email, client_id, refresh_token, group_id
    FROM accounts
    WHERE status = 'active'
      AND {REFRESHABLE_OUTLOOK_ACCOUNT_WHERE}
"""


def is_refreshable_outlook_account(
    account_type: Optional[str],
    *,
    provider: Optional[str] = None,
) -> bool:
    """仅 Outlook（以及历史空 account_type）允许进入 OAuth token 刷新链路。
    排除 provider=cloudflare_temp_mail（CF pool 账号无 OAuth token）。"""
    # CF pool 账号永远不应进入刷新链路
    if provider and str(provider).strip() == "cloudflare_temp_mail":
        return False
    if account_type is None:
        return True
    return isinstance(account_type, str) and account_type.strip().lower() == "outlook"


INVALID_TOKEN_FAILED_LIST_LIMIT = 200

INVALID_TOKEN_ERROR_KEYWORDS = ("invalid_grant", "aadsts70000")
