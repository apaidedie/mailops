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

from .access import _account_can_read, _preferred_probe_method
from .errors import ExternalApiError
from .messages import list_messages_for_external
from .timefmt import _parse_datetime, _utcnow

# Outlook IMAP 回退服务器（保持与内部接口一致）

def _probe_now_iso() -> str:
    return _utcnow().replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _probe_summary_from_row(row: Any) -> Dict[str, Any]:
    if not row:
        return {
            "upstream_probe_ok": None,
            "probe_method": "",
            "last_probe_at": "",
            "last_probe_error": "",
        }
    return {
        "upstream_probe_ok": None if row["probe_ok"] is None else bool(row["probe_ok"]),
        "probe_method": row["probe_method"] or "",
        "last_probe_at": row["last_probe_at"] or "",
        "last_probe_error": row["last_probe_error"] or "",
    }

def get_upstream_probe_summary(scope_type: str, scope_key: str) -> Dict[str, Any]:
    from outlook_web.db import get_db

    db = get_db()
    row = db.execute(
        """
        SELECT scope_type, scope_key, email_addr, probe_method, probe_ok, last_probe_at, last_probe_error
        FROM external_upstream_probes
        WHERE scope_type = ? AND scope_key = ?
        """,
        (scope_type, scope_key),
    ).fetchone()
    return _probe_summary_from_row(row)

def _is_probe_summary_fresh(summary: Dict[str, Any], cache_ttl_seconds: int) -> bool:
    last_probe_at = summary.get("last_probe_at") or ""
    if not last_probe_at:
        return False
    probed_at = _parse_datetime(last_probe_at)
    if not probed_at:
        return False
    age_seconds = (_utcnow() - probed_at).total_seconds()
    return age_seconds <= max(0, int(cache_ttl_seconds))

def record_upstream_probe_summary(
    *,
    scope_type: str,
    scope_key: str,
    email_addr: str,
    probe_ok: Optional[bool],
    probe_method: str = "",
    last_probe_error: str = "",
    last_probe_at: Optional[str] = None,
) -> Dict[str, Any]:
    from outlook_web.db import get_db

    db = get_db()
    probe_at = last_probe_at or _probe_now_iso()
    db.execute(
        """
        INSERT INTO external_upstream_probes
            (scope_type, scope_key, email_addr, probe_method, probe_ok, last_probe_at, last_probe_error, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(scope_type, scope_key)
        DO UPDATE SET
            email_addr = excluded.email_addr,
            probe_method = excluded.probe_method,
            probe_ok = excluded.probe_ok,
            last_probe_at = excluded.last_probe_at,
            last_probe_error = excluded.last_probe_error,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            scope_type,
            scope_key,
            email_addr or "",
            probe_method or "",
            None if probe_ok is None else int(bool(probe_ok)),
            probe_at,
            str(last_probe_error or "")[:500],
        ),
    )
    db.commit()
    return {
        "upstream_probe_ok": probe_ok,
        "probe_method": probe_method or "",
        "last_probe_at": probe_at,
        "last_probe_error": str(last_probe_error or "")[:500],
    }

def _probe_error_message(exc: Exception) -> str:
    if isinstance(exc, ExternalApiError):
        return str(exc.message or exc.code or "探测失败")
    return str(exc)[:500] or type(exc).__name__

def probe_account_upstream(
    account: Dict[str, Any],
    *,
    folder: str = "inbox",
    cache_ttl_seconds: int = 60,
    force: bool = False,
) -> Dict[str, Any]:
    email_addr = str(account.get("email") or "").strip()
    preferred_method = _preferred_probe_method(account)
    cached = get_upstream_probe_summary("account", email_addr) if email_addr else {}
    if email_addr and (not force) and _is_probe_summary_fresh(cached, cache_ttl_seconds):
        return cached

    last_probe_at = _probe_now_iso()
    try:
        _emails, method = list_messages_for_external(email_addr=email_addr, folder=folder, top=1, skip=0)
        summary = record_upstream_probe_summary(
            scope_type="account",
            scope_key=email_addr,
            email_addr=email_addr,
            probe_ok=True,
            probe_method=str(method or preferred_method),
            last_probe_error="",
            last_probe_at=last_probe_at,
        )
    except Exception as exc:
        summary = record_upstream_probe_summary(
            scope_type="account",
            scope_key=email_addr,
            email_addr=email_addr,
            probe_ok=False,
            probe_method=preferred_method,
            last_probe_error=_probe_error_message(exc),
            last_probe_at=last_probe_at,
        )
    record_upstream_probe_summary(
        scope_type="instance",
        scope_key="__instance__",
        email_addr=email_addr,
        probe_ok=summary.get("upstream_probe_ok"),
        probe_method=summary.get("probe_method") or preferred_method,
        last_probe_error=summary.get("last_probe_error") or "",
        last_probe_at=summary.get("last_probe_at") or last_probe_at,
    )
    return summary

def _pick_instance_probe_account() -> Optional[Dict[str, Any]]:
    candidates = accounts_repo.load_accounts()
    for account in candidates:
        if _account_can_read(account):
            return account
    return None

def probe_instance_upstream(*, cache_ttl_seconds: int = 60, force: bool = False) -> Dict[str, Any]:
    cached = get_upstream_probe_summary("instance", "__instance__")
    if (not force) and _is_probe_summary_fresh(cached, cache_ttl_seconds):
        return cached

    account = _pick_instance_probe_account()
    if not account:
        return cached

    return probe_account_upstream(account, cache_ttl_seconds=cache_ttl_seconds, force=force)
