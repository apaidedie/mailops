from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROVIDER_CONFIG_FILE_ENV = "OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE"
_PROVIDER_CONFIG_SECTIONS = ("mailbox_providers", "providers", "mailbox", "env")


class ProviderConfigFileError(RuntimeError):
    def __init__(self, code: str, message: str, *, path: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path


def _getenv(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value != "" else default


def _get_provider_config_file_path() -> str:
    return _getenv(PROVIDER_CONFIG_FILE_ENV, "") or ""


def _resolve_provider_config_file_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _read_provider_config_file() -> dict[str, Any]:
    path_text = _get_provider_config_file_path()
    if not path_text:
        return {}
    path = _resolve_provider_config_file_path(path_text)
    if not path.exists():
        raise ProviderConfigFileError(
            "PROVIDER_CONFIG_FILE_NOT_FOUND",
            f"Provider config file not found: {path}",
            path=str(path),
        )
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".toml":
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        else:
            raise ProviderConfigFileError(
                "PROVIDER_CONFIG_FILE_UNSUPPORTED_FORMAT",
                "Provider config file must use .json or .toml",
                path=str(path),
            )
    except ProviderConfigFileError:
        raise
    except Exception as exc:
        raise ProviderConfigFileError(
            "PROVIDER_CONFIG_FILE_PARSE_FAILED",
            f"Provider config file parse failed: {path}: {exc}",
            path=str(path),
        ) from exc
    if not isinstance(data, dict):
        raise ProviderConfigFileError(
            "PROVIDER_CONFIG_FILE_INVALID_SHAPE",
            f"Provider config file must contain an object: {path}",
            path=str(path),
        )
    return data


def _provider_config_entry(*keys: str, strict: bool = True) -> tuple[Any, str]:
    try:
        data = _read_provider_config_file()
    except ProviderConfigFileError:
        if strict:
            raise
        return None, ""
    if not data:
        return None, ""
    containers: list[dict[str, Any]] = [data]
    for section in _PROVIDER_CONFIG_SECTIONS:
        section_value = data.get(section)
        if isinstance(section_value, dict):
            containers.append(section_value)
    for container in containers:
        for key in keys:
            if key in container:
                return container[key], key
    return None, ""


def _provider_override_info(env_key: str, *config_keys: str, strict: bool = True) -> dict[str, Any]:
    env_value = _getenv(env_key, "") or ""
    if env_value:
        return {"value": env_value, "source": "env", "key": env_key, "path": ""}
    config_status = get_provider_config_file_status()
    if config_status.get("enabled") and config_status.get("error_code") and not strict:
        return {
            "value": "",
            "source": "config_file_error",
            "key": env_key,
            "path": config_status.get("path") or "",
            "error_code": config_status.get("error_code") or "PROVIDER_CONFIG_FILE_INVALID",
            "error": config_status.get("error") or "Provider config file is invalid",
            "config_file": config_status,
        }
    file_value, file_key = _provider_config_entry(env_key, *config_keys, strict=strict)
    if file_value not in (None, ""):
        return {
            "value": file_value,
            "source": "config_file",
            "key": file_key or (config_keys[0] if config_keys else env_key),
            "path": _get_provider_config_file_path(),
        }
    return {"value": "", "source": "", "key": env_key, "path": _get_provider_config_file_path()}


def get_provider_config_file_status() -> dict[str, Any]:
    path = _get_provider_config_file_path()
    status: dict[str, Any] = {
        "enabled": bool(path),
        "env": PROVIDER_CONFIG_FILE_ENV,
        "formats": ["json", "toml"],
        "path": path,
        "resolved_path": "",
        "loaded": False,
        "error_code": "",
        "error": "",
    }
    if not path:
        return status
    status["resolved_path"] = str(_resolve_provider_config_file_path(path))
    try:
        data = _read_provider_config_file()
    except ProviderConfigFileError as exc:
        status["error_code"] = exc.code
        status["error"] = exc.message
        status["resolved_path"] = exc.path or status["resolved_path"]
        return status
    status["loaded"] = True
    status["sections"] = [section for section in _PROVIDER_CONFIG_SECTIONS if isinstance(data.get(section), dict)]
    return status


def require_secret_key() -> str:
    secret_key = _getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY environment variable is required. "
            "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    return secret_key


def get_database_path() -> str:
    return _getenv("DATABASE_PATH", "data/outlook_accounts.db") or "data/outlook_accounts.db"


def get_login_password_default() -> str:
    return _getenv("LOGIN_PASSWORD", "admin123") or "admin123"


def get_gptmail_base_url() -> str:
    return _getenv("GPTMAIL_BASE_URL", "https://mail.chatgpt.org.uk") or "https://mail.chatgpt.org.uk"


def get_gptmail_api_key_default() -> str:
    return _getenv("GPTMAIL_API_KEY", "") or ""


def get_temp_mail_base_url() -> str:
    """正式临时邮箱上游地址；环境变量保持兼容旧 GPTMAIL_* 命名。"""
    return get_gptmail_base_url()


def get_temp_mail_api_key_default() -> str:
    """正式临时邮箱 API Key 默认值；环境变量保持兼容旧 GPTMAIL_* 命名。"""
    return get_gptmail_api_key_default()


def get_temp_mail_provider_override() -> str:
    """Deployment-level runtime provider override. Empty means use database setting."""
    return str(get_temp_mail_provider_override_info().get("value") or "").strip()


def get_temp_mail_provider_override_info(*, strict: bool = True) -> dict[str, Any]:
    return _provider_override_info("TEMP_MAIL_PROVIDER", "temp_mail_provider", "runtime_temp_mail_provider", strict=strict)


def get_external_pool_default_provider_override() -> str:
    """Deployment-level default provider for external pool claims. Empty keeps request-driven auto behavior."""
    return str(get_external_pool_default_provider_override_info().get("value") or "").strip()


def get_external_pool_default_provider_override_info(*, strict: bool = True) -> dict[str, Any]:
    return _provider_override_info(
        "EXTERNAL_POOL_DEFAULT_PROVIDER",
        "pool_default_provider",
        "pool_claim_provider",
        "external_pool_default_provider",
        strict=strict,
    )


def get_active_mailbox_providers_override() -> Any:
    """Deployment-level mailbox provider allowlist. Empty means all providers stay active."""
    return get_active_mailbox_providers_override_info().get("value") or ""


def get_active_mailbox_providers_override_info(*, strict: bool = True) -> dict[str, Any]:
    return _provider_override_info("ACTIVE_MAILBOX_PROVIDERS", "active_mailbox_providers", "active_providers", strict=strict)


def env_true(key: str, default: bool) -> bool:
    """
    与旧实现保持一致：只有值为 'true'（忽略大小写）才视为 True；其它值均为 False。
    """
    value = _getenv(key, "true" if default else "false") or ("true" if default else "false")
    return value.lower() == "true"


def get_allow_login_password_change() -> bool:
    return env_true("ALLOW_LOGIN_PASSWORD_CHANGE", True)


def get_scheduler_autostart_default() -> bool:
    return env_true("SCHEDULER_AUTOSTART", True)


def get_log_format() -> str:
    """Runtime log format. Invalid values keep the local-friendly text default."""
    value = (_getenv("LOG_FORMAT", "text") or "text").lower()
    return value if value in {"text", "json"} else "text"


def get_log_level() -> str:
    """Runtime log level with PERF_LOGGING kept as a backward-compatible DEBUG fallback."""
    value = (_getenv("LOG_LEVEL", "") or "").upper()
    if value in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return value
    return "DEBUG" if env_true("PERF_LOGGING", False) else "INFO"


def _normalize_external_api_cors_origin(value: str) -> str:
    text = str(value or "").strip()
    if not text or "*" in text:
        return ""
    try:
        parsed = urlsplit(text)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            return ""
        if parsed.path not in {"", "/"}:
            return ""
        port = parsed.port
    except (TypeError, ValueError):
        return ""
    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port_suffix = f":{port}" if port is not None else ""
    return f"{scheme}://{host}{port_suffix}"


def get_external_api_cors_origin_config() -> dict[str, Any]:
    """Return normalized exact browser origins without exposing rejected values."""
    raw_value = _getenv("EXTERNAL_API_CORS_ORIGINS", "") or ""
    entries = raw_value.replace("\r", "\n").replace(",", "\n").splitlines()
    origins: list[str] = []
    invalid_origin_count = 0
    for entry in entries:
        text = entry.strip()
        if not text:
            continue
        normalized = _normalize_external_api_cors_origin(text)
        if not normalized:
            invalid_origin_count += 1
            continue
        if normalized not in origins:
            origins.append(normalized)
    return {
        "origins": origins,
        "invalid_origin_count": invalid_origin_count,
        "env": "EXTERNAL_API_CORS_ORIGINS",
    }


def get_external_api_cors_allow_chrome_extension() -> bool:
    """Keep existing browser-extension CORS support unless explicitly disabled."""
    return env_true("EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION", True)


def get_trusted_proxies() -> list[str]:
    """
    获取受信任的代理 IP 列表。
    用于验证 X-Forwarded-For 头的来源是否可信。

    环境变量 TRUSTED_PROXIES 格式：逗号分隔的 CIDR 或 IP，如：
    - "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16" (内网代理)
    - "127.0.0.1" (本地代理)
    - "" (空表示不信任任何代理，直接使用 remote_addr)

    默认值：空字符串（安全默认 - 不信任任何代理）
    """
    proxies_str = _getenv("TRUSTED_PROXIES", "")
    if not proxies_str:
        return []
    return [p.strip() for p in proxies_str.split(",") if p.strip()]


def get_proxy_fix_enabled() -> bool:
    """
    是否启用 ProxyFix 中间件。

    只有在应用部署在反向代理后面，并且配置了 TRUSTED_PROXIES 时才应启用。
    默认：False（安全默认）
    """
    return env_true("PROXY_FIX_ENABLED", False)


def get_security_headers_enabled() -> bool:
    """Whether to attach baseline browser security headers to every response."""
    return env_true("SECURITY_HEADERS_ENABLED", True)


def get_security_headers_force_hsts() -> bool:
    """Force HSTS even when Flask does not see the request as HTTPS."""
    return env_true("SECURITY_HEADERS_FORCE_HSTS", False)


def get_security_hsts_max_age() -> int:
    """HSTS max-age in seconds. Defaults to one year; invalid values fall back safely."""
    raw_value = _getenv("SECURITY_HSTS_MAX_AGE", "31536000") or "31536000"
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        return 31536000


# ---- OAuth Token 工具 ----


def get_oauth_tool_enabled() -> bool:
    """是否启用 Token 获取工具。默认启用。"""
    return env_true("OAUTH_TOOL_ENABLED", True)


def get_oauth_client_id_default() -> str:
    """OAuth 工具默认 Client ID（环境变量层）。"""
    return _getenv("OAUTH_CLIENT_ID", "") or ""


def get_oauth_client_secret_default() -> str:
    """OAuth 工具默认 Client Secret（环境变量层）。"""
    return _getenv("OAUTH_CLIENT_SECRET", "") or ""


def get_oauth_redirect_uri_default() -> str:
    """OAuth 工具默认 Redirect URI（环境变量层）。"""
    return _getenv("OAUTH_REDIRECT_URI", "") or ""


def get_oauth_scope_default() -> str:
    """OAuth 工具默认 Scope（环境变量层）。"""
    default_scope = "offline_access https://outlook.office.com/IMAP.AccessAsUser.All"
    return _getenv("OAUTH_SCOPE", default_scope) or default_scope


def get_oauth_tenant_default() -> str:
    """OAuth 工具默认 Tenant（环境变量层）。"""
    return _getenv("OAUTH_TENANT", "consumers") or "consumers"
