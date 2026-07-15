from __future__ import annotations

from typing import Any

from outlook_web.services.mailbox_catalog import list_unified_mailboxes
from outlook_web.services.provider_catalog import get_external_api_readiness_summary


INTEGRATION_BUNDLE_ENDPOINT = "/api/v1/external/integration-bundle"


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _status(value: Any, *, default: str = "unknown") -> str:
    text = str(value or "").strip().lower()
    return text or default


def _provider_status(value: str) -> str:
    normalized = _status(value)
    if normalized in {"ready", "needs_config", "degraded"}:
        return normalized
    if normalized == "inactive":
        return "needs_config"
    return "unknown"


def _external_status(value: str) -> str:
    normalized = _status(value)
    if normalized in {"ready", "needs_config", "degraded", "restricted"}:
        return normalized
    if normalized in {"disabled", "inactive"}:
        return "restricted"
    return "unknown"


def _mailbox_inventory_status(total: int, catalog_ok: bool) -> str:
    if not catalog_ok:
        return "degraded"
    return "ready" if total > 0 else "empty"


def _overall_status(*, inventory_status: str, provider_status: str, external_status: str) -> str:
    if "degraded" in {inventory_status, provider_status, external_status}:
        return "degraded"
    if inventory_status == "empty":
        return "empty"
    if provider_status == "needs_config" or external_status == "needs_config":
        return "needs_config"
    if provider_status == "ready" and external_status in {"ready", "restricted"}:
        return "ready"
    return "unknown"


def _action(key: str, label: str, detail: str, target: str, priority: str, status: str) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "detail": detail,
        "target": target,
        "priority": priority,
        "status": status,
    }


def _actions(
    *,
    inventory: dict[str, Any],
    provider: dict[str, Any],
    external: dict[str, Any],
    overall_status: str,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if _to_int(inventory.get("total")) <= 0:
        items.append(
            _action(
                "add_mailbox_inventory",
                "接入邮箱库存",
                "导入 Outlook/IMAP 账号或创建临时邮箱后，统一目录才有可读库存。",
                "mailbox",
                "high",
                "needs_config",
            )
        )
    if _to_int(provider.get("needs_config")) > 0 or provider.get("status") in {"needs_config", "unknown"}:
        items.append(
            _action(
                "review_provider_config",
                "检查 Provider 配置",
                "补齐启用 Provider 的本地配置，并确认来源优先级。",
                "settings:api-security",
                "high",
                "needs_config",
            )
        )
    if external.get("mailbox_directory_status") in {"empty", "degraded", "unknown"}:
        items.append(
            _action(
                "check_external_mailbox_directory",
                "检查外部邮箱目录",
                "确认 /api/v1/external/mailboxes 能返回统一目录摘要。",
                "/api/v1/external/mailboxes?page=1&page_size=1",
                "medium",
                "degraded" if external.get("mailbox_directory_status") == "degraded" else "neutral",
            )
        )
    if external.get("status") in {"ready", "restricted"}:
        items.append(
            _action(
                "read_integration_bundle",
                "读取 Integration Bundle",
                "外部项目可从一站式 bundle 获取认证占位、端点和动作计划。",
                INTEGRATION_BUNDLE_ENDPOINT,
                "low",
                "ready",
            )
        )
    if not items:
        items.append(
            _action(
                "continue_operations",
                "继续运营监控",
                "统一邮箱、Provider 路由和外部 API 已具备基础可用状态。",
                "dashboard:summary",
                "low",
                "ready" if overall_status == "ready" else "neutral",
            )
        )
    return items[:4]


def get_overview_command_center_degraded() -> dict[str, Any]:
    inventory = {"status": "degraded", "total": 0, "account": 0, "temp": 0, "providers": 0}
    provider = {
        "status": "unknown",
        "ready": 0,
        "active": 0,
        "needs_config": 0,
        "dynamic_create": 0,
        "temp_providers": 0,
        "account_providers": 0,
    }
    external = {
        "status": "degraded",
        "discovery_status": "unavailable",
        "mailbox_directory_status": "degraded",
        "task_temp_mailbox_status": "unknown",
        "pool_status": "unknown",
        "integration_bundle_endpoint": INTEGRATION_BUNDLE_ENDPOINT,
    }
    return {
        "overall_status": "degraded",
        "mailbox_inventory": inventory,
        "provider_readiness": provider,
        "external_api": external,
        "actions": [
            _action(
                "reload_overview_summary",
                "重新读取总览",
                "本地聚合状态暂不可用，请刷新总览或检查服务日志。",
                "dashboard:summary",
                "high",
                "degraded",
            )
        ],
    }


def get_overview_command_center() -> dict[str, Any]:
    """Build a secret-free dashboard projection from existing service contracts."""
    try:
        mailbox_payload = list_unified_mailboxes(page=1, page_size=1)
        summary = mailbox_payload.get("summary") if isinstance(mailbox_payload.get("summary"), dict) else {}
        pagination = mailbox_payload.get("pagination") if isinstance(mailbox_payload.get("pagination"), dict) else {}
        facets = mailbox_payload.get("facets") if isinstance(mailbox_payload.get("facets"), dict) else {}
        provider_context = mailbox_payload.get("provider_context") if isinstance(mailbox_payload.get("provider_context"), dict) else {}
        readiness = provider_context.get("readiness_summary") if isinstance(provider_context.get("readiness_summary"), dict) else {}
        totals = readiness.get("totals") if isinstance(readiness.get("totals"), dict) else {}

        provider_facets = facets.get("providers") if isinstance(facets.get("providers"), list) else []
        total = _to_int(pagination.get("total_count") or summary.get("total"))
        inventory = {
            "status": _mailbox_inventory_status(total, True),
            "total": total,
            "account": _to_int(summary.get("account")),
            "temp": _to_int(summary.get("temp")),
            "providers": _to_int(totals.get("providers")) or len(provider_facets),
        }
        provider = {
            "status": _provider_status(str(readiness.get("overall_status") or "")),
            "ready": _to_int(totals.get("ready_providers")),
            "active": _to_int(totals.get("active_providers")),
            "needs_config": _to_int(totals.get("needs_config_providers")),
            "dynamic_create": _to_int(totals.get("dynamic_create_providers")),
            "temp_providers": _to_int(totals.get("temp_providers")),
            "account_providers": _to_int(totals.get("account_providers")),
        }

        readiness_payload = get_external_api_readiness_summary(consumer=None, database_ok=True, upstream_probe_ok=None)
        discovery = readiness_payload.get("discovery") if isinstance(readiness_payload.get("discovery"), dict) else {}
        mailbox_directory = readiness_payload.get("mailbox_directory") if isinstance(readiness_payload.get("mailbox_directory"), dict) else {}
        task_temp_mailbox = readiness_payload.get("task_temp_mailbox") if isinstance(readiness_payload.get("task_temp_mailbox"), dict) else {}
        pool = readiness_payload.get("pool") if isinstance(readiness_payload.get("pool"), dict) else {}
        next_endpoints = discovery.get("next_endpoints") if isinstance(discovery.get("next_endpoints"), dict) else {}
        external = {
            "status": _external_status(str(readiness_payload.get("status") or "")),
            "discovery_status": "available" if _status(discovery.get("status")) == "ready" else _status(discovery.get("status")),
            "mailbox_directory_status": _status(mailbox_directory.get("status")),
            "task_temp_mailbox_status": _status(task_temp_mailbox.get("status")),
            "pool_status": _status(pool.get("status")),
            "integration_bundle_endpoint": str(next_endpoints.get("integration_bundle") or INTEGRATION_BUNDLE_ENDPOINT),
        }
        overall = _overall_status(
            inventory_status=str(inventory["status"]),
            provider_status=str(provider["status"]),
            external_status=str(external["status"]),
        )
        return {
            "overall_status": overall,
            "mailbox_inventory": inventory,
            "provider_readiness": provider,
            "external_api": external,
            "actions": _actions(inventory=inventory, provider=provider, external=external, overall_status=overall),
        }
    except Exception:
        return get_overview_command_center_degraded()
