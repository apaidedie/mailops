from __future__ import annotations

from typing import Any

from outlook_web.repositories import settings as settings_repo

from .constants import (
    _BRIDGE_OPERATOR_CANONICAL,
    _BRIDGE_OPERATOR_FAMILY,
    COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
)


# Late-bound normalize to avoid circular import with catalog.
def _normalize_provider_name(value: Any) -> str:
    from . import catalog as _catalog

    return _catalog._normalize_provider_name(value)


def _canonical_bridge_operator_provider(provider_name: str | None) -> str:
    """Map Compatible Temp Mail Bridge dual-register keys to the operator canonical key."""
    name = _normalize_provider_name(provider_name)
    if name in _BRIDGE_OPERATOR_FAMILY:
        return _BRIDGE_OPERATOR_CANONICAL
    return name


def get_operator_temp_mail_default_provider(*, strict: bool = False) -> str:
    """Return the operator/API-facing default temp provider key.

    Runtime/settings may still store historical dual-register names such as
    ``custom_domain_temp_mail``. After diagnostics/guide collapse to a single
    ``legacy_bridge`` row, discovery defaults must project the same canonical key
    so external clients never see a default missing from guide.providers.
    """
    return _canonical_bridge_operator_provider(settings_repo.get_temp_mail_runtime_provider_name(strict=strict))


def _merge_unique_str_list(*groups: Any) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        for raw in group:
            value = str(raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


def _collapse_bridge_operator_provider_rows(
    rows: list[dict[str, Any]],
    *,
    kind_key: str = "kind",
    provider_key: str = "provider",
) -> list[dict[str, Any]]:
    """Collapse dual Compatible Temp Mail Bridge rows for diagnostics/guide surfaces.

    Full catalog/registry still dual-registers `custom_domain_temp_mail` and
    `legacy_bridge` for inventory source compatibility. Operator-facing discovery
    surfaces should expose a single canonical bridge row.
    """
    collapsed: list[dict[str, Any]] = []
    bridge_index: int | None = None
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        kind = str(item.get(kind_key) or "").strip().lower()
        provider = _normalize_provider_name(item.get(provider_key))
        if kind == "temp" and provider in _BRIDGE_OPERATOR_FAMILY:
            item[provider_key] = _BRIDGE_OPERATOR_CANONICAL
            if bridge_index is None:
                bridge_index = len(collapsed)
                collapsed.append(item)
                continue
            existing = collapsed[bridge_index]
            prefer_incoming = (
                provider == _BRIDGE_OPERATOR_CANONICAL
                and _normalize_provider_name(existing.get(provider_key)) != _BRIDGE_OPERATOR_CANONICAL
            )
            base = item if prefer_incoming else existing
            other = existing if prefer_incoming else item
            merged = {
                **other,
                **base,
                provider_key: _BRIDGE_OPERATOR_CANONICAL,
                "label": base.get("label") or other.get("label") or COMPATIBLE_TEMP_MAIL_BRIDGE_LABEL,
                "active": bool(existing.get("active", True)) or bool(item.get("active", True)),
                "configured": bool(existing.get("configured", True)) or bool(item.get("configured", True)),
                "missing_config": _merge_unique_str_list(existing.get("missing_config"), item.get("missing_config")),
                "can_dynamic_create": bool(existing.get("can_dynamic_create")) or bool(item.get("can_dynamic_create")),
            }
            # Preserve readiness fields when present on either side.
            if existing.get("status") or item.get("status"):
                prefer_ready = "ready" in {str(existing.get("status") or ""), str(item.get("status") or "")}
                if prefer_ready:
                    ready_row = existing if str(existing.get("status") or "") == "ready" else item
                    merged["status"] = ready_row.get("status")
                    merged["status_reason"] = ready_row.get("status_reason") or merged.get("status_reason")
                    merged["readiness_status"] = ready_row.get("readiness_status") or ready_row.get("status")
                    merged["readiness_reason"] = ready_row.get("readiness_reason") or ready_row.get("status_reason")
            settings_ui = base.get("settings_ui") if isinstance(base.get("settings_ui"), dict) else {}
            other_ui = other.get("settings_ui") if isinstance(other.get("settings_ui"), dict) else {}
            if settings_ui or other_ui:
                merged_ui = {**other_ui, **settings_ui}
                merged_ui["aliases"] = _merge_unique_str_list(
                    other_ui.get("aliases"),
                    settings_ui.get("aliases"),
                    list(_BRIDGE_OPERATOR_FAMILY - {_BRIDGE_OPERATOR_CANONICAL}),
                )
                merged["settings_ui"] = merged_ui
            collapsed[bridge_index] = merged
            continue
        collapsed.append(item)
    return collapsed
