from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from outlook_web.temp_mail_registry import _REGISTRY, get_registry_snapshot


DEFAULT_PROVIDER_CAPABILITIES = {
    "delete_mailbox": False,
    "delete_message": True,
    "clear_messages": True,
}

_FALSE_CAPABILITY_VALUES = {"0", "false", "no", "off", "disabled", "disable", "n"}
_TRUE_CAPABILITY_VALUES = {"1", "true", "yes", "on", "enabled", "enable", "y"}


def _coerce_capability_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _FALSE_CAPABILITY_VALUES:
            return False
        if normalized in _TRUE_CAPABILITY_VALUES:
            return True
        if not normalized:
            return default
    return bool(value)


def normalize_provider_capabilities(raw_capabilities: Any = None) -> dict[str, bool]:
    capabilities = raw_capabilities if isinstance(raw_capabilities, dict) else {}
    return {
        "delete_mailbox": _coerce_capability_bool(
            capabilities.get("delete_mailbox"), DEFAULT_PROVIDER_CAPABILITIES["delete_mailbox"]
        ),
        "delete_message": _coerce_capability_bool(
            capabilities.get("delete_message"), DEFAULT_PROVIDER_CAPABILITIES["delete_message"]
        ),
        "clear_messages": _coerce_capability_bool(
            capabilities.get("clear_messages"), DEFAULT_PROVIDER_CAPABILITIES["clear_messages"]
        ),
    }


def register_provider(cls: type["TempMailProviderBase"]) -> type["TempMailProviderBase"]:
    """类装饰器：将 Provider 注册到全局注册表。"""
    raw_name = getattr(cls, "provider_name", None)
    resolved_name = ""

    # 常规路径：显式声明 provider_name
    if isinstance(raw_name, str):
        resolved_name = raw_name.strip()
        # 显式给了空字符串，视为无效，不做回退
        if not resolved_name and "provider_name" in getattr(cls, "__dict__", {}):
            return cls
    elif raw_name is not None:
        # 非字符串显式值（如 int）直接忽略
        return cls

    # 兼容路径：未声明 provider_name 时，用类名自动派生
    if not resolved_name and "provider_name" not in getattr(cls, "__dict__", {}):
        class_name = getattr(cls, "__name__", "")
        if class_name:
            resolved_name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower().strip("_")

    if resolved_name:
        _REGISTRY[resolved_name] = cls
    return cls


def get_registry() -> dict[str, type["TempMailProviderBase"]]:
    """返回注册表快照（只读副本）。"""
    return get_registry_snapshot()


class TempMailProviderBase(ABC):
    provider_name: str = ""
    provider_label: str = ""
    provider_version: str = "0.0.0"
    provider_author: str = ""
    provider_capabilities: dict[str, bool] = dict(DEFAULT_PROVIDER_CAPABILITIES)
    config_schema: dict[str, Any] = {}

    def get_capabilities(self) -> dict[str, bool]:
        return normalize_provider_capabilities(getattr(self, "provider_capabilities", None))

    @abstractmethod
    def get_options(self) -> dict[str, Any]:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        options = self.get_options()
        return {
            "success": True,
            "method": "get_options",
            "network_probe": False,
            "details": {
                "domain_count": len(options.get("domains") or []),
                "api_base_url": options.get("api_base_url") or "",
                "configured": options.get("configured", True),
                "missing_config": options.get("missing_config") or [],
            },
        }

    @abstractmethod
    def create_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def generate_mailbox(self, *, prefix: str | None = None, domain: str | None = None) -> dict[str, Any]:
        return self.create_mailbox(prefix=prefix, domain=domain)

    @abstractmethod
    def delete_mailbox(self, mailbox: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_messages(self, mailbox: dict[str, Any]) -> list[dict[str, Any]] | None:
        raise NotImplementedError

    @abstractmethod
    def get_message_detail(self, mailbox: dict[str, Any], message_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, mailbox: dict[str, Any], message_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def clear_messages(self, mailbox: dict[str, Any]) -> bool:
        raise NotImplementedError


def _ensure_builtin_providers_loaded() -> None:
    """确保内置 Provider 在基类模块导入后完成注册。"""
    try:
        import outlook_web.services.temp_mail_provider_cf  # noqa: F401
        import outlook_web.services.temp_mail_provider_custom  # noqa: F401
        import outlook_web.services.temp_mail_provider_public  # noqa: F401
    except Exception:
        # 基类模块不能因为内置 provider 导入失败而不可用
        return


_ensure_builtin_providers_loaded()
