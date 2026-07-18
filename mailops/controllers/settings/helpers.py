from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from flask import jsonify, request

from mailops import config
from mailops.audit import log_audit
from mailops.db import get_db
from mailops.errors import build_error_payload
from mailops.repositories import external_api_keys as external_api_keys_repo
from mailops.repositories import settings as settings_repo
from mailops.security.auth import login_required
from mailops.security.crypto import (
    decrypt_data,
    encrypt_data,
    hash_password,
    is_encrypted,
)
from mailops.services import webhook_push
from mailops.services.external_api_contract_check import get_external_api_contract_check
from mailops.services.provider_catalog import get_mailbox_provider_catalog, temp_mail_provider_label
from mailops.services.verification_extractor import probe_verification_ai_runtime

# ==================== 设置 API ====================


def _mask_secret_value(value: str, head: int = 4, tail: int = 4) -> str:
    if not value:
        return ""
    safe_value = str(value)
    if len(safe_value) <= head + tail:
        return "*" * len(safe_value)
    return safe_value[:head] + ("*" * (len(safe_value) - head - tail)) + safe_value[-tail:]


def _plugin_settings_contract() -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for provider in get_mailbox_provider_catalog(include_inactive=True, strict=False):
        if provider.get("kind") != "temp" or provider.get("config_source") != "plugin":
            continue
        configuration = provider.get("configuration") if isinstance(provider.get("configuration"), dict) else {}
        secret_keys = set(configuration.get("secret_settings") or [])
        for setting_key in configuration.get("settings_keys") or []:
            key = str(setting_key or "").strip()
            if key.startswith("plugin."):
                fields[key] = {"secret": key in secret_keys}
    return fields


def _parse_allowed_emails_input(raw: Any) -> list[str]:
    if raw in (None, "", []):
        return []
    if isinstance(raw, list):
        values = raw
    else:
        text = str(raw).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            values = parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            values = [item.strip() for item in text.replace("\r", "\n").replace(",", "\n").split("\n")]

    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        email_addr = str(item or "").strip().lower()
        if not email_addr or "@" not in email_addr or email_addr in seen:
            continue
        seen.add(email_addr)
        result.append(email_addr)
    return result


def _parse_bool_input(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return default


def _coerce_int_range(raw: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _parse_temp_mail_domains_input(raw: Any) -> list[dict[str, Any]]:
    if raw in (None, "", []):
        return []

    values = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            values = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            values = [item.strip() for item in text.replace("\r", "\n").split("\n")]

    if not isinstance(values, list):
        raise ValueError("temp_mail_domains 必须是数组")

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            enabled = _parse_bool_input(item.get("enabled"), default=True)
        else:
            name = str(item or "").strip()
            enabled = True
        if not name or name in seen:
            continue
        seen.add(name)
        result.append({"name": name, "enabled": enabled})
    return result


def _parse_temp_mail_prefix_rules_input(raw: Any) -> dict[str, Any]:
    if raw in (None, "", {}):
        return {
            "min_length": 1,
            "max_length": 32,
            "pattern": r"^[a-z0-9][a-z0-9._-]*$",
        }

    value = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            value = {}
        else:
            value = json.loads(text)

    if not isinstance(value, dict):
        raise ValueError("temp_mail_prefix_rules 必须是对象")

    min_length = _coerce_int_range(value.get("min_length", 1), 1, minimum=1, maximum=64)
    max_length = _coerce_int_range(value.get("max_length", 32), 32, minimum=min_length, maximum=128)
    pattern = str(value.get("pattern") or r"^[a-z0-9][a-z0-9._-]*$").strip()
    if not pattern:
        pattern = r"^[a-z0-9][a-z0-9._-]*$"
    return {
        "min_length": min_length,
        "max_length": max_length,
        "pattern": pattern,
    }


def _parse_emailnator_email_types_input(raw: Any) -> list[str]:
    return settings_repo.normalize_emailnator_email_types(raw, strict=True)


def _parse_mailbox_provider_list_input(raw: Any) -> list[str]:
    return settings_repo.normalize_mailbox_provider_list(raw)


def _is_valid_notification_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))


def _json_error(
    code: str,
    message: str,
    *,
    status: int = 400,
    message_en: str | None = None,
    details: Any = None,
    http_status: int | None = None,
    extra: dict[str, Any] | None = None,
):
    payload = build_error_payload(
        code=code,
        message=message,
        message_en=message_en,
        err_type="ValidationError" if status < 500 else "ServiceError",
        status=status,
        details=details,
    )
    body: dict[str, Any] = {"success": False, "error": payload}
    if extra:
        body.update(extra)
    return jsonify(body), (http_status if http_status is not None else status)


def _ensure_email_service_available() -> None:
    from mailops.services import email_push

    email_push.get_email_push_service_config()
