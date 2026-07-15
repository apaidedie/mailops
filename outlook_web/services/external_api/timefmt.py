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

# Outlook IMAP 回退服务器（保持与内部接口一致）

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _parse_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    # 1) ISO 8601（Graph 常见：2026-03-08T12:00:00Z）
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # 2) RFC2822（IMAP Date header 常见）
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _format_datetime(dt: Optional[datetime], fallback: str = "") -> tuple[str, int]:
    if not dt:
        return (fallback or "", 0)
    try:
        dt = dt.astimezone(timezone.utc).replace(microsecond=0)
        return (dt.isoformat().replace("+00:00", "Z"), int(dt.timestamp()))
    except Exception:
        return (fallback or "", 0)

def _extract_email_address(value: str) -> str:
    """从 `Name <addr>` 中提取 addr；解析失败则原样返回。"""
    try:
        _name, addr = parseaddr(str(value or ""))
        return addr or str(value or "")
    except Exception:
        return str(value or "")

def claimed_at_to_timestamp(claimed_at: str) -> Optional[int]:
    """将 claimed_at ISO string 转为 Unix timestamp（整数），解析失败返回 None。"""
    if not claimed_at:
        return None
    try:
        dt = _parse_datetime(claimed_at)
        if dt:
            return int(dt.timestamp())
    except Exception:
        pass
    return None
