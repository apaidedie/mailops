from __future__ import annotations

import json
import os
from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

from mailops import config
from mailops.db import create_sqlite_connection, get_db
from mailops.security.crypto import decrypt_data

DEFAULT_TEMP_MAIL_PROVIDER = "custom_domain_temp_mail"
LEGACY_TEMP_MAIL_PROVIDER = "legacy_bridge"
CLOUDFLARE_TEMP_MAIL_PROVIDER = "cloudflare_temp_mail"
MAIL_TM_TEMP_MAIL_PROVIDER = "mail_tm"
TEMPMAIL_LOL_TEMP_MAIL_PROVIDER = "tempmail_lol"
EMAILNATOR_TEMP_MAIL_PROVIDER = "emailnator"
DUCKMAIL_TEMP_MAIL_PROVIDER = "duckmail"
LEGACY_TEMP_MAIL_PROVIDER_NAMES = {"legacy_bridge", "legacy_gptmail", "gptmail", "temp_mail"}
MAILTM_DEFAULT_API_BASE = "https://api.mail.tm"
DUCKMAIL_DEFAULT_API_BASE = "https://api.duckmail.sbs"
EMAILNATOR_DEFAULT_EMAIL_TYPES = ("public_gmail_plus",)
EMAILNATOR_VALID_EMAIL_TYPES = (
    "public_email_domain",
    "public_gmail_plus",
    "public_gmail_dot",
    "public_googlemail",
    "private_email_domain",
    "private_gmail_plus",
    "private_gmail_dot",
    "private_googlemail",
)


def get_setting(key: str, default: str = "") -> str:
    """获取设置值"""
    db = None
    temp_conn = False
    try:
        db = get_db()
    except RuntimeError:
        db = create_sqlite_connection()
        temp_conn = True

    try:
        cursor = db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
    finally:
        if temp_conn and db is not None:
            db.close()


def set_setting(key: str, value: str, *, commit: bool = True) -> bool:
    """设置值"""
    db = None
    temp_conn = False
    try:
        db = get_db()
    except RuntimeError:
        db = create_sqlite_connection()
        temp_conn = True

    try:
        db.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (key, value),
        )
        if commit:
            db.commit()
        return True
    except Exception:
        return False
    finally:
        if temp_conn and db is not None:
            db.close()


def get_all_settings() -> Dict[str, str]:
    """获取所有设置"""
    db = None
    temp_conn = False
    try:
        db = get_db()
    except RuntimeError:
        db = create_sqlite_connection()
        temp_conn = True

    try:
        cursor = db.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        if temp_conn and db is not None:
            db.close()


def get_login_password() -> str:
    """获取登录密码（优先从数据库读取）"""
    password = get_setting("login_password")
    return password if password else config.get_login_password_default()


def get_legacy_gptmail_api_key() -> str:
    """兼容读取 legacy gptmail_api_key。"""
    return get_setting("gptmail_api_key")


def get_temp_mail_api_key() -> str:
    """获取正式临时邮箱 API Key，并兼容 legacy gptmail_api_key 回退。"""
    api_key = get_setting("temp_mail_api_key")
    if api_key:
        return api_key
    legacy_api_key = get_legacy_gptmail_api_key()
    if legacy_api_key:
        return legacy_api_key
    return config.get_temp_mail_api_key_default()


def get_gptmail_api_key() -> str:
    """legacy bridge 兼容入口。"""
    return get_temp_mail_api_key()


def normalize_temp_mail_provider_name(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return DEFAULT_TEMP_MAIL_PROVIDER
    if normalized.lower() in LEGACY_TEMP_MAIL_PROVIDER_NAMES:
        return LEGACY_TEMP_MAIL_PROVIDER
    return normalized


def get_supported_temp_mail_provider_names() -> set[str]:
    from mailops.temp_mail_registry import _REGISTRY

    return set(_REGISTRY.keys())


def is_supported_temp_mail_provider_name(value: str | None) -> bool:
    return normalize_temp_mail_provider_name(value) in get_supported_temp_mail_provider_names()


def validate_temp_mail_provider_name(value: str | None) -> str:
    normalized = normalize_temp_mail_provider_name(value)
    if normalized not in get_supported_temp_mail_provider_names():
        raise ValueError("临时邮箱 Provider 配置无效")
    return normalized


def get_temp_mail_provider(*, strict: bool = True) -> str:
    provider_override = config.get_temp_mail_provider_override_info(strict=strict)
    override_value = str(provider_override.get("value") or "").strip()
    if override_value:
        return normalize_temp_mail_provider_name(override_value)
    return normalize_temp_mail_provider_name(get_setting("temp_mail_provider", DEFAULT_TEMP_MAIL_PROVIDER))


def get_temp_mail_runtime_provider_name(provider_name: str | None = None, *, strict: bool = True) -> str:
    if provider_name is not None:
        return normalize_temp_mail_provider_name(provider_name)
    return get_temp_mail_provider(strict=strict)


def get_pool_default_provider(*, strict: bool = True) -> str:
    provider_override = config.get_external_pool_default_provider_override_info(strict=strict)
    override_value = str(provider_override.get("value") or "").strip()
    value = override_value if override_value else get_setting("pool_default_provider", "")
    normalized = str(value or "").strip().lower()
    if not normalized or normalized == "auto":
        return ""
    return normalized


def normalize_mailbox_provider_list(raw: Any) -> list[str]:
    if raw in (None, "", []):
        return []
    value = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            value = parsed if isinstance(parsed, list) else text
        except (json.JSONDecodeError, TypeError):
            value = text
    if isinstance(value, str):
        values = [item.strip() for item in value.replace("\r", "\n").replace(",", "\n").split("\n")]
    elif isinstance(value, list):
        values = value
    else:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        name = str(item or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def get_active_mailbox_provider_names(*, strict: bool = True) -> list[str]:
    provider_override = config.get_active_mailbox_providers_override_info(strict=strict)
    if provider_override.get("source") in {"env", "config_file"}:
        raw_value = provider_override.get("value")
    else:
        raw_value = get_setting("active_mailbox_providers", "")
    return normalize_mailbox_provider_list(raw_value)


def get_active_mailbox_provider_name_set(*, strict: bool = True) -> set[str]:
    return set(get_active_mailbox_provider_names(strict=strict))


def mailbox_provider_filter_is_active(*, strict: bool = True) -> bool:
    return bool(get_active_mailbox_provider_names(strict=strict))


def get_temp_mail_api_base_url() -> str:
    base_url = get_setting("temp_mail_api_base_url")
    return normalize_temp_mail_api_base_url(base_url if base_url else config.get_temp_mail_base_url())


def get_mailtm_api_base() -> str:
    return _normalize_api_base(os.environ.get("MAILTM_API_BASE", "")) or MAILTM_DEFAULT_API_BASE


def get_tempmail_lol_api_key() -> str:
    """获取 TempMail.lol API Key，兼容历史设置名与环境变量别名。"""
    value = get_setting("tempmail_lol_api_key", "").strip() or get_setting("temp_mail_lol_api_key", "").strip()
    if not value:
        return os.environ.get("TEMPMAIL_LOL_API_KEY", "").strip() or os.environ.get("TEMP_MAIL_LOL_API_KEY", "").strip()
    try:
        return decrypt_data(value)
    except Exception:
        return value


def _normalize_api_base(value: str | None) -> str:
    return str(value or "").strip().rstrip("/")


def _looks_like_locale_segment(value: str) -> bool:
    text = str(value or "").strip().lower()
    if len(text) == 2 and text.isalpha():
        return True
    if "-" not in text:
        return False
    language, region = text.split("-", 1)
    return len(language) == 2 and language.isalpha() and 2 <= len(region) <= 3 and region.isalpha()


def normalize_temp_mail_api_base_url(value: str | None) -> str:
    text = _normalize_api_base(value)
    if not text:
        return ""

    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    lowered = [part.lower() for part in parts]
    if lowered and lowered[-1] == "api":
        if len(parts) == 1:
            parts = []
        elif len(parts) == 2 and _looks_like_locale_segment(parts[0]):
            parts = []
        else:
            parts = parts[:-1]
    # Docs locale roots such as /zh or /en-US are not part of the API base.
    if len(parts) == 1 and _looks_like_locale_segment(parts[0]):
        parts = []

    normalized_path = "/" + "/".join(parts) if parts else ""
    return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))


def get_cf_worker_base_url() -> str:
    """获取 Cloudflare Temp Email Worker 独立部署地址（与GPTMail设置完全隔离）。"""
    value = get_setting("cf_worker_base_url", "").strip()
    if value:
        return value
    return os.environ.get("CF_WORKER_BASE_URL", "").strip()


def get_cf_worker_admin_key() -> str:
    """获取 Cloudflare Worker ADMIN_PASSWORDS 中的密码值（自动解密 enc: 格式）。"""
    value = get_setting("cf_worker_admin_key", "").strip()
    if not value:
        return os.environ.get("CF_WORKER_ADMIN_KEY", "").strip()
    try:
        return decrypt_data(value)
    except Exception:
        # 兼容历史明文值：解密失败时直接返回明文
        return value


def get_emailnator_api_key() -> str:
    """获取 Emailnator RapidAPI Key（自动解密 enc: 格式）。"""
    value = get_setting("emailnator_api_key", "").strip()
    if not value:
        return os.environ.get("EMAILNATOR_API_KEY", "").strip()
    try:
        return decrypt_data(value)
    except Exception:
        return value


def normalize_emailnator_email_types(raw: Any, *, strict: bool = False) -> list[str]:
    default_types = list(EMAILNATOR_DEFAULT_EMAIL_TYPES)
    if raw in (None, "", []):
        return default_types
    value = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return default_types
        try:
            value = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            value = [item.strip() for item in text.replace("\r", "\n").replace(",", "\n").split("\n")]
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        if strict:
            raise ValueError("emailnator_email_types 必须是数组")
        return default_types
    result: list[str] = []
    seen: set[str] = set()
    invalid: list[str] = []
    for item in value:
        type_name = str(item or "").strip()
        if not type_name:
            continue
        if type_name not in EMAILNATOR_VALID_EMAIL_TYPES:
            invalid.append(type_name)
            continue
        if type_name in seen:
            continue
        seen.add(type_name)
        result.append(type_name)
    if invalid and strict:
        raise ValueError("emailnator_email_types 包含无效值: " + ", ".join(invalid))
    return result or default_types


def get_emailnator_email_types() -> list[str]:
    """获取 Emailnator 创建邮箱时使用的 type 白名单。"""
    env_value = os.environ.get("EMAILNATOR_EMAIL_TYPES", "").strip()
    stored_value = get_setting("emailnator_email_types", "").strip()
    if stored_value and not (env_value and stored_value == json.dumps(list(EMAILNATOR_DEFAULT_EMAIL_TYPES))):
        return normalize_emailnator_email_types(stored_value)
    return normalize_emailnator_email_types(env_value or stored_value)


def get_duckmail_api_base() -> str:
    env_value = _normalize_api_base(os.environ.get("DUCKMAIL_API_BASE", ""))
    stored_value = _normalize_api_base(get_setting("duckmail_api_base", ""))
    if stored_value and not (env_value and stored_value == DUCKMAIL_DEFAULT_API_BASE):
        return stored_value
    return env_value or DUCKMAIL_DEFAULT_API_BASE


def get_duckmail_bearer_token() -> str:
    """获取 DuckMail Bearer Token（自动解密 enc: 格式）。"""
    value = get_setting("duckmail_bearer_token", "").strip()
    if not value:
        return os.environ.get("DUCKMAIL_BEARER_TOKEN", "").strip()
    try:
        return decrypt_data(value)
    except Exception:
        return value


def get_temp_mail_domains() -> list[dict[str, Any]]:
    raw = get_setting("temp_mail_domains", "[]")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return value if isinstance(value, list) else []


def get_temp_mail_default_domain() -> str:
    return get_setting("temp_mail_default_domain", "").strip()


def get_temp_mail_prefix_rules() -> dict[str, Any]:
    raw = get_setting("temp_mail_prefix_rules", "{}")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def get_cf_worker_domains() -> list[dict[str, Any]]:
    """获取 CF Worker 独立域名列表（v0.3 Tab 重构）。"""
    raw = get_setting("cf_worker_domains", "[]")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return value if isinstance(value, list) else []


def get_cf_worker_default_domain() -> str:
    """获取 CF Worker 默认域名（v0.3 Tab 重构）。"""
    return get_setting("cf_worker_default_domain", "").strip()


def get_cf_worker_prefix_rules() -> dict[str, Any]:
    """获取 CF Worker 前缀规则（v0.3 Tab 重构）。"""
    _default_rules: dict[str, Any] = {
        "min_length": 1,
        "max_length": 32,
        "pattern": "^[a-z0-9][a-z0-9._-]*$",
    }
    raw = get_setting("cf_worker_prefix_rules", "{}")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _default_rules
    if not isinstance(value, dict) or not value:
        return _default_rules
    return value


def get_external_api_key() -> str:
    """
    获取对外开放 API Key。

    - 若数据库为空，返回空字符串
    - 若为 enc: 加密格式，自动解密
    - 若为历史明文（兼容），直接返回明文
    - 解密失败时返回空字符串（避免影响外部接口鉴权逻辑）
    """
    value = get_setting("external_api_key") or ""
    if not value:
        return ""
    try:
        return decrypt_data(value)
    except Exception:
        return ""


def get_webhook_notification_enabled() -> bool:
    return get_setting("webhook_notification_enabled", "false").lower() == "true"


def get_webhook_notification_url() -> str:
    return get_setting("webhook_notification_url", "").strip()


def get_webhook_notification_token() -> str:
    """
    获取 Webhook Token。

    - 若数据库为空，返回空字符串
    - 若为 enc: 加密格式，自动解密
    - 解密失败时返回空字符串
    """
    value = get_setting("webhook_notification_token", "").strip()
    if not value:
        return ""
    try:
        return decrypt_data(value)
    except Exception:
        return ""


def get_webhook_notification_token_masked(head: int = 4, tail: int = 4) -> str:
    """Webhook Token 脱敏展示：前 N 位 + 若干 * + 后 N 位。"""
    token = get_webhook_notification_token()
    if not token:
        return ""
    safe_value = str(token)
    if len(safe_value) <= head + tail:
        return "*" * len(safe_value)
    return safe_value[:head] + ("*" * (len(safe_value) - head - tail)) + safe_value[-tail:]


def get_verification_ai_enabled() -> bool:
    return get_setting("verification_ai_enabled", "false").lower() == "true"


def get_verification_ai_base_url() -> str:
    return get_setting("verification_ai_base_url", "").strip()


def get_verification_ai_model() -> str:
    return get_setting("verification_ai_model", "").strip()


def get_verification_ai_api_key() -> str:
    """
    获取验证码 AI API Key。

    - 若为空，返回空字符串
    - 若为 enc: 加密格式，自动解密
    - 若为历史明文（兼容），直接返回明文
    """
    value = get_setting("verification_ai_api_key", "").strip()
    if not value:
        return ""
    try:
        return decrypt_data(value)
    except Exception:
        # 兼容历史明文
        return value


def get_external_api_key_masked(head: int = 4, tail: int = 4) -> str:
    """对外 API Key 脱敏展示：前 N 位 + 若干 * + 后 N 位。"""
    key = get_external_api_key()
    if not key:
        return ""
    safe_value = str(key)
    if len(safe_value) <= head + tail:
        return "*" * len(safe_value)
    return safe_value[:head] + ("*" * (len(safe_value) - head - tail)) + safe_value[-tail:]


# ── P1：公网模式安全配置 ──────────────────────────────


def get_external_api_public_mode() -> bool:
    """公网模式是否开启（默认关闭，保持 P0 受控私有行为）。"""
    return get_setting("external_api_public_mode", "false").lower() == "true"


def get_external_api_ip_whitelist() -> list:
    """IP 白名单列表（JSON 数组，支持 CIDR 如 '192.168.1.0/24'）。"""
    import json

    raw = get_setting("external_api_ip_whitelist", "[]")
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def get_external_api_rate_limit() -> int:
    """每分钟每 IP 最大请求数（默认 60）。"""
    try:
        val = int(get_setting("external_api_rate_limit_per_minute", "60"))
        return max(1, val)
    except (ValueError, TypeError):
        return 60


def get_external_api_disable_wait_message() -> bool:
    """是否禁用 wait-message 端点（默认不禁用）。"""
    return get_setting("external_api_disable_wait_message", "false").lower() == "true"


def get_external_api_disable_raw_content() -> bool:
    """是否禁用 raw 端点（默认不禁用）。"""
    return get_setting("external_api_disable_raw_content", "false").lower() == "true"


def get_pool_external_enabled() -> bool:
    return get_setting("pool_external_enabled", "false").lower() == "true"


def get_external_api_disable_pool_claim_random() -> bool:
    return get_setting("external_api_disable_pool_claim_random", "false").lower() == "true"


def get_external_api_disable_pool_claim_release() -> bool:
    return get_setting("external_api_disable_pool_claim_release", "false").lower() == "true"


def get_external_api_disable_pool_claim_complete() -> bool:
    return get_setting("external_api_disable_pool_claim_complete", "false").lower() == "true"


def get_external_api_disable_pool_stats() -> bool:
    return get_setting("external_api_disable_pool_stats", "false").lower() == "true"


def get_ui_layout_v2() -> dict:
    """读取前端布局状态"""
    import json

    raw = get_setting("ui_layout_v2", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def set_ui_layout_v2(layout: dict) -> None:
    """写入前端布局状态"""
    import json

    set_setting("ui_layout_v2", json.dumps(layout, ensure_ascii=False))


# ── Telegram 代理配置 ──────────────────────────────


def get_telegram_proxy_url() -> str:
    """获取 Telegram 推送使用的系统级代理 URL（明文存储，如 socks5://host:port）。"""
    return get_setting("telegram_proxy_url", "").strip()


def set_telegram_proxy_url(url: str) -> bool:
    """保存 Telegram 代理 URL。"""
    return set_setting("telegram_proxy_url", url.strip())


def get_telegram_bot_token() -> str:
    """获取 Telegram Bot Token（支持 enc: 加密格式）。"""
    from mailops.security.crypto import decrypt_data, is_encrypted

    value = get_setting("telegram_bot_token", "").strip()
    if not value:
        return ""
    if is_encrypted(value):
        try:
            return decrypt_data(value)
        except Exception:
            return ""
    return value
