from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from mailops.db import get_db
from mailops.repositories import temp_emails as temp_emails_repo
from mailops.services.mailbox_directory_contract import (
    MAILBOX_SUMMARY_FIELDS,
    get_mailbox_catalog_contract,
)
from mailops.services.provider_catalog import (
    account_provider_label,
    get_external_mailbox_read_contract,
    get_mailbox_directory_provider_context,
    temp_mail_provider_label,
)

MAILBOX_CATALOG_CONTRACT = get_mailbox_catalog_contract()

_VALID_KIND_FILTERS = set(MAILBOX_CATALOG_CONTRACT["filters"]["kind"])
_VALID_STATUS_FILTERS = set(MAILBOX_CATALOG_CONTRACT["filters"]["status"])
_VALID_READ_CAPABILITY_FILTERS = set(MAILBOX_CATALOG_CONTRACT["filters"]["read_capability"])
_VALID_ACTION_FILTERS = set(MAILBOX_CATALOG_CONTRACT["filters"]["action"])
_VALID_SORT_FILTERS = set(MAILBOX_CATALOG_CONTRACT["filters"]["sort"])


class MailboxCatalogError(ValueError):
    def __init__(self, code: str, message: str, *, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}


@dataclass(frozen=True)
class MailboxSourceLoader:
    kind: str
    load: Callable[[], list[dict[str, Any]]]


def _normalize_filter(value: Any, *, default: str) -> str:
    return str(value or default).strip().lower() or default


def _coerce_bounded_int(value: Any, *, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = default
    normalized = max(minimum, normalized)
    if maximum is not None:
        normalized = min(maximum, normalized)
    return normalized


def _email_domain(email: str) -> str:
    text = str(email or "").strip()
    return text.rsplit("@", 1)[-1].lower() if "@" in text else ""


def _load_json_object(raw_value: Any) -> dict[str, Any]:
    if isinstance(raw_value, dict):
        return dict(raw_value)
    if not isinstance(raw_value, str) or not raw_value.strip():
        return {}
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _account_read_capability(account_type: str, provider: str) -> str:
    if provider == "cloudflare_temp_mail":
        return "temp_provider"
    return "imap" if account_type == "imap" else "graph"


def _normalize_provider_name(provider: Any, *, default: str = "") -> str:
    return str(provider or default).strip().lower() or default


# Compatible Temp Mail Bridge dual-register keys (registry keeps both for source
# compatibility). Inventory/facets/filter collapse to the canonical operator key.
_BRIDGE_PROVIDER_CANONICAL = "legacy_bridge"
_BRIDGE_PROVIDER_ALIASES = frozenset(
    {
        "custom_domain_temp_mail",
        "legacy_bridge",
        "gptmail",
        "legacy_gptmail",
        "temp_mail",
    }
)


def _canonical_inventory_provider(provider: Any, *, default: str = "") -> str:
    """Collapse bridge dual-register aliases for operator-facing inventory/facets."""
    name = _normalize_provider_name(provider, default=default)
    if name in _BRIDGE_PROVIDER_ALIASES:
        return _BRIDGE_PROVIDER_CANONICAL
    return name


def _provider_filter_matches(item_provider: Any, filter_provider: str) -> bool:
    if filter_provider == "all":
        return True
    return _canonical_inventory_provider(item_provider) == _canonical_inventory_provider(filter_provider)


def _account_actions(account_type: str, provider: str) -> dict[str, bool]:
    temp_meta_backed = provider == "cloudflare_temp_mail"
    return {
        "read_messages": True,
        "refresh_auth": account_type == "outlook" and not temp_meta_backed,
        "edit": True,
        "delete": not temp_meta_backed,
        "delete_remote_mailbox": False,
        "delete_message": False,
        "clear_messages": False,
    }


def _temp_actions(capabilities: dict[str, Any]) -> dict[str, bool]:
    return {
        "read_messages": True,
        "refresh_auth": False,
        "edit": False,
        "delete": True,
        "delete_remote_mailbox": bool(capabilities.get("delete_mailbox")),
        "delete_message": bool(capabilities.get("delete_message")),
        "clear_messages": bool(capabilities.get("clear_messages")),
    }


def _external_action_for_email(action: dict[str, Any], email: str) -> dict[str, Any]:
    payload = copy.deepcopy(action)
    query_fields = [str(item or "") for item in payload.get("query_fields") or []]
    fixed_query = payload.get("fixed_query") if isinstance(payload.get("fixed_query"), dict) else {}
    query = copy.deepcopy(fixed_query)
    if "email" in query_fields:
        query["email"] = email
    if query:
        payload["query"] = query
    return payload


def _external_read_actions_for_email(email: str) -> tuple[dict[str, Any], dict[str, Any]]:
    read_contract = get_external_mailbox_read_contract(lifecycle="none")
    actions = {
        str(name): _external_action_for_email(action, email)
        for name, action in (read_contract.get("next_actions") or {}).items()
        if isinstance(action, dict)
    }
    return read_contract, actions


def _account_internal_actions(*, email: str, source_id: int, group_id: Any) -> dict[str, Any]:
    return {
        "open_mailbox": {
            "mode": "standard",
            "kind": "account",
            "email": email,
            "source_id": source_id,
            "group_id": group_id,
        },
        "read_messages": {
            "method": "GET",
            "endpoint": "/api/emails/{email}",
            "path_fields": ["email"],
            "path": {"email": email},
            "query": {"folder": "inbox"},
        },
        "read_message_detail": {
            "method": "GET",
            "endpoint": "/api/email/{email}/{message_id}",
            "path_fields": ["email", "message_id"],
            "path": {"email": email},
            "query": {"folder": "inbox"},
        },
        "extract_verification": {
            "method": "GET",
            "endpoint": "/api/emails/{email}/extract-verification",
            "path_fields": ["email"],
            "path": {"email": email},
        },
    }


def _temp_internal_actions(*, email: str, source_id: int) -> dict[str, Any]:
    return {
        "open_mailbox": {
            "mode": "temp-emails",
            "kind": "temp",
            "email": email,
            "source_id": source_id,
            "group_id": None,
        },
        "read_messages": {
            "method": "GET",
            "endpoint": "/api/temp-emails/{email}/messages",
            "path_fields": ["email"],
            "path": {"email": email},
            "query": {"sync_remote": True},
        },
        "read_message_detail": {
            "method": "GET",
            "endpoint": "/api/temp-emails/{email}/messages/{message_id}",
            "path_fields": ["email", "message_id"],
            "path": {"email": email},
        },
        "extract_verification": {
            "method": "GET",
            "endpoint": "/api/temp-emails/{email}/extract-verification",
            "path_fields": ["email"],
            "path": {"email": email},
        },
    }


def _mailbox_action_contract(
    *,
    email: str,
    read_capability: str,
    internal_actions: dict[str, Any],
) -> dict[str, Any]:
    external_read_contract, external_actions = _external_read_actions_for_email(email)
    return {
        "version": 1,
        "read_by": ["email"],
        "read_capability": read_capability,
        "external_read_contract": {
            "source": "provider_catalog.external_mailbox_read_contract",
            "lifecycle": "none",
            "email_query_field": external_read_contract.get("email_query_field") or "email",
            "claim_token_query_field": external_read_contract.get("claim_token_query_field") or "claim_token",
        },
        "external": external_actions,
        "internal": internal_actions,
    }


def _account_mailbox_from_row(row: Any) -> dict[str, Any]:
    account = dict(row)
    account_type = str(account.get("account_type") or "outlook").strip().lower() or "outlook"
    provider = _normalize_provider_name(account.get("provider"), default="outlook" if account_type == "outlook" else "custom")
    email = str(account.get("email") or "").strip()
    status = str(account.get("status") or "active").strip().lower() or "active"
    pool_status = str(account.get("pool_status") or "").strip().lower()
    temp_meta = _load_json_object(account.get("temp_mail_meta"))
    provider_label = (
        temp_mail_provider_label(provider) if provider == "cloudflare_temp_mail" else account_provider_label(provider)
    )
    source_id = int(account.get("id") or 0)
    group_id = account.get("group_id")
    read_capability = _account_read_capability(account_type, provider)

    return {
        "id": f"account:{account.get('id')}",
        "source_id": source_id,
        "kind": "account",
        "email": email,
        "domain": str(account.get("email_domain") or _email_domain(email)),
        "status": status,
        "pool_status": pool_status,
        "source": "account",
        "provider": provider,
        "provider_label": provider_label or provider,
        "account_type": account_type,
        "read_capability": read_capability,
        "group": {
            "id": group_id,
            "name": account.get("group_name") or "默认分组",
            "color": account.get("group_color") or "#666666",
        },
        "labels": [str(tag.get("name") or "") for tag in (account.get("tags") or []) if str(tag.get("name") or "")],
        "remark": str(account.get("remark") or ""),
        "latest": {
            "email_subject": str(account.get("latest_email_subject") or ""),
            "email_from": str(account.get("latest_email_from") or ""),
            "email_folder": str(account.get("latest_email_folder") or ""),
            "email_received_at": str(account.get("latest_email_received_at") or ""),
            "verification_code": str(account.get("latest_verification_code") or ""),
            "verification_folder": str(account.get("latest_verification_folder") or ""),
            "verification_received_at": str(account.get("latest_verification_received_at") or ""),
        },
        "timestamps": {
            "created_at": str(account.get("created_at") or ""),
            "updated_at": str(account.get("updated_at") or ""),
            "last_refresh_at": str(account.get("last_refresh_at") or ""),
        },
        "notification_enabled": bool(account.get("telegram_push_enabled")),
        "actions": _account_actions(account_type, provider),
        "action_contract": _mailbox_action_contract(
            email=email,
            read_capability=read_capability,
            internal_actions=_account_internal_actions(email=email, source_id=source_id, group_id=group_id),
        ),
        "meta": {
            "mailbox_type": "pool_temp" if provider == "cloudflare_temp_mail" else "account",
            "temp_provider_name": str(temp_meta.get("provider_name") or provider) if temp_meta else "",
        },
    }


def _temp_mailbox_from_descriptor(mailbox: dict[str, Any]) -> dict[str, Any]:
    source = _normalize_provider_name(mailbox.get("source"), default="custom_domain_temp_mail")
    provider = _normalize_provider_name(
        mailbox.get("provider_name") or source,
        default="custom_domain_temp_mail",
    )
    capabilities = (mailbox.get("meta") or {}).get("provider_capabilities") or {}
    status = str(mailbox.get("status") or "active").strip().lower() or "active"
    pool_status = str((mailbox.get("record") or {}).get("pool_status") or "").strip().lower()
    email = str(mailbox.get("email") or "").strip()
    source_id = int((mailbox.get("record") or {}).get("id") or 0)
    read_capability = str(mailbox.get("read_capability") or "temp_provider")

    return {
        "id": f"temp:{(mailbox.get('record') or {}).get('id')}",
        "source_id": source_id,
        "kind": "temp",
        "email": email,
        "domain": str(mailbox.get("domain") or _email_domain(email)),
        "status": status,
        "pool_status": pool_status,
        "source": source,
        "provider": provider,
        "provider_label": temp_mail_provider_label(provider),
        "account_type": "temp",
        "read_capability": read_capability,
        "group": {"id": None, "name": "临时邮箱", "color": "#7c3aed"},
        "labels": list((mailbox.get("meta") or {}).get("provider_labels") or []),
        "remark": "",
        "latest": {
            "email_subject": "",
            "email_from": "",
            "email_folder": "",
            "email_received_at": "",
            "verification_code": "",
            "verification_folder": "",
            "verification_received_at": "",
        },
        "timestamps": {
            "created_at": str(mailbox.get("created_at") or ""),
            "updated_at": str(mailbox.get("updated_at") or ""),
            "last_refresh_at": "",
        },
        "notification_enabled": False,
        "actions": _temp_actions(capabilities),
        "action_contract": _mailbox_action_contract(
            email=email,
            read_capability=read_capability,
            internal_actions=_temp_internal_actions(email=email, source_id=source_id),
        ),
        "meta": {
            "mailbox_type": str(mailbox.get("mailbox_type") or "user"),
            "visible_in_ui": bool(mailbox.get("visible_in_ui")),
        },
    }


def _load_tags_by_account_ids(account_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not account_ids:
        return {}
    db = get_db()
    placeholders = ",".join(["?"] * len(account_ids))
    rows = db.execute(
        f"""
        SELECT at.account_id, t.id, t.name, t.color, t.created_at
        FROM account_tags at
        JOIN tags t ON t.id = at.tag_id
        WHERE at.account_id IN ({placeholders})
        ORDER BY at.account_id ASC, t.created_at DESC
        """,
        account_ids,
    ).fetchall()
    tags_by_account: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        tag = dict(row)
        account_id = tag.pop("account_id", None)
        if account_id is None:
            continue
        tags_by_account.setdefault(int(account_id), []).append(tag)
    return tags_by_account


def _load_account_mailboxes() -> list[dict[str, Any]]:
    db = get_db()
    rows = db.execute("""
        SELECT
            a.id, a.email, a.account_type, a.provider, a.group_id, a.remark, a.status,
            a.created_at, a.updated_at, a.last_refresh_at, a.telegram_push_enabled,
            a.latest_email_subject, a.latest_email_from, a.latest_email_folder, a.latest_email_received_at,
            a.latest_verification_code, a.latest_verification_folder, a.latest_verification_received_at,
            a.pool_status, a.email_domain, a.temp_mail_meta,
            g.name AS group_name, g.color AS group_color
        FROM accounts a
        LEFT JOIN groups g ON a.group_id = g.id
        ORDER BY a.created_at DESC, a.id DESC
        """).fetchall()
    accounts = [dict(row) for row in rows]
    account_ids = [int(account["id"]) for account in accounts if account.get("id") is not None]
    tags_by_account = _load_tags_by_account_ids(account_ids)
    for account in accounts:
        account_id = int(account.get("id") or 0)
        account["tags"] = tags_by_account.get(account_id, [])
    return [_account_mailbox_from_row(account) for account in accounts]


def _load_temp_mailboxes() -> list[dict[str, Any]]:
    mailboxes = temp_emails_repo.load_temp_emails(visible_only=True, mailbox_type="user", view="descriptor")
    return [_temp_mailbox_from_descriptor(mailbox) for mailbox in mailboxes]


MAILBOX_SOURCE_LOADERS: tuple[MailboxSourceLoader, ...] = (
    MailboxSourceLoader(kind="account", load=_load_account_mailboxes),
    MailboxSourceLoader(kind="temp", load=_load_temp_mailboxes),
)


def get_mailbox_source_loader_kinds() -> list[str]:
    return [loader.kind for loader in MAILBOX_SOURCE_LOADERS]


def _load_mailboxes_from_sources(loaders: Sequence[MailboxSourceLoader] | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for loader in MAILBOX_SOURCE_LOADERS if loaders is None else loaders:
        items.extend(loader.load())
    return items


def _matches_status(item: dict[str, Any], status: str) -> bool:
    if status == "all":
        return True
    return status in {str(item.get("status") or "").lower(), str(item.get("pool_status") or "").lower()}


def _matches_read_capability(item: dict[str, Any], read_capability: str) -> bool:
    if read_capability == "all":
        return True
    return str(item.get("read_capability") or "").strip().lower() == read_capability


def _matches_action(item: dict[str, Any], action: str) -> bool:
    if action == "all":
        return True
    actions = item.get("actions") if isinstance(item.get("actions"), dict) else {}
    return bool(actions.get(action))


def _apply_context_filters(
    items: list[dict[str, Any]],
    *,
    kind: str,
    status: str,
    read_capability: str,
    action: str,
    search: str,
) -> list[dict[str, Any]]:
    filtered = [
        item
        for item in items
        if (kind == "all" or item.get("kind") == kind)
        and _matches_status(item, status)
        and _matches_read_capability(item, read_capability)
        and _matches_action(item, action)
    ]
    normalized_search = str(search or "").strip().lower()
    if not normalized_search:
        return filtered
    return [
        item
        for item in filtered
        if normalized_search in str(item.get("email") or "").lower()
        or normalized_search in str(item.get("domain") or "").lower()
        or normalized_search in str(item.get("provider") or "").lower()
        or normalized_search in str(item.get("provider_label") or "").lower()
        or normalized_search in str(item.get("remark") or "").lower()
        or normalized_search in str((item.get("group") or {}).get("name") or "").lower()
        or any(normalized_search in str(label or "").lower() for label in (item.get("labels") or []))
    ]


def _apply_account_email_scope(items: list[dict[str, Any]], allowed_account_emails: list[str] | None) -> list[dict[str, Any]]:
    allowed = {str(item or "").strip().lower() for item in (allowed_account_emails or []) if str(item or "").strip()}
    if not allowed:
        return items
    return [
        item
        for item in items
        if str(item.get("kind") or "").strip().lower() != "account" or str(item.get("email") or "").strip().lower() in allowed
    ]


def _apply_provider_filter(items: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
    if provider == "all":
        return items
    return [item for item in items if _provider_filter_matches(item.get("provider"), provider)]


def _provider_facets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facets: dict[str, dict[str, Any]] = {}
    kinds_by_provider: dict[str, set[str]] = {}
    for item in items:
        provider = _canonical_inventory_provider(item.get("provider"))
        if not provider:
            continue
        if provider == _BRIDGE_PROVIDER_CANONICAL:
            label = temp_mail_provider_label(provider) or str(item.get("provider_label") or provider)
        else:
            label = str(item.get("provider_label") or provider)
        facet = facets.setdefault(
            provider,
            {
                "provider": provider,
                "label": label,
                "kind": str(item.get("kind") or ""),
                "count": 0,
            },
        )
        facet["count"] += 1
        kind = str(item.get("kind") or "").strip().lower()
        if kind:
            kinds_by_provider.setdefault(provider, set()).add(kind)

    normalized: list[dict[str, Any]] = []
    for provider, facet in facets.items():
        kinds = sorted(kinds_by_provider.get(provider) or [])
        normalized.append({**facet, "kind": kinds[0] if len(kinds) == 1 else "mixed"})
    return sorted(normalized, key=lambda item: (str(item.get("label") or "").lower(), str(item.get("provider") or "")))


def _mailbox_provider_inventory(items: list[dict[str, Any]]) -> dict[str, Any]:
    providers: dict[tuple[str, str], dict[str, Any]] = {}
    totals = {
        "mailboxes": 0,
        "account_mailboxes": 0,
        "temp_mailboxes": 0,
    }
    for item in items:
        kind = str(item.get("kind") or "").strip().lower()
        provider = _canonical_inventory_provider(item.get("provider"))
        if not kind or not provider:
            continue
        totals["mailboxes"] += 1
        if kind == "account":
            totals["account_mailboxes"] += 1
        elif kind == "temp":
            totals["temp_mailboxes"] += 1
        if provider == _BRIDGE_PROVIDER_CANONICAL:
            label = temp_mail_provider_label(provider) or str(item.get("provider_label") or provider)
        else:
            label = str(item.get("provider_label") or provider)
        row = providers.setdefault(
            (kind, provider),
            {
                "kind": kind,
                "provider": provider,
                "label": label,
                "mailbox_count": 0,
                "account_count": 0,
                "temp_count": 0,
                "read_capabilities": [],
            },
        )
        row["mailbox_count"] += 1
        if kind == "account":
            row["account_count"] += 1
        elif kind == "temp":
            row["temp_count"] += 1
        read_capability = str(item.get("read_capability") or "").strip().lower()
        if read_capability and read_capability not in row["read_capabilities"]:
            row["read_capabilities"].append(read_capability)
    rows = sorted(
        providers.values(),
        key=lambda row: (str(row.get("kind") or ""), str(row.get("label") or "").lower(), str(row.get("provider") or "")),
    )
    return {
        "version": 1,
        "totals": {**totals, "providers": len(rows)},
        "providers": rows,
    }


def _fixed_definition_facets(
    items: list[dict[str, Any]],
    *,
    definitions: list[dict[str, Any]],
    value_key: str,
    matches: Callable[[dict[str, Any], str], bool],
) -> list[dict[str, Any]]:
    facets: list[dict[str, Any]] = []
    for definition in definitions:
        if not isinstance(definition, dict):
            continue
        value = str(definition.get(value_key) or "").strip().lower()
        if not value:
            continue
        facet = {
            value_key: value,
            "label": str(definition.get("label") or value),
            "label_en": str(definition.get("label_en") or definition.get("label") or value),
            "count": sum(1 for item in items if matches(item, value)),
        }
        if "summary_key" in definition:
            facet["summary_key"] = str(definition.get("summary_key") or "")
        facets.append(facet)
    return facets


def _kind_facets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _fixed_definition_facets(
        items,
        definitions=MAILBOX_CATALOG_CONTRACT.get("kind_definitions") or [],
        value_key="kind",
        matches=lambda item, kind: str(item.get("kind") or "").strip().lower() == kind,
    )


def _status_facets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _fixed_definition_facets(
        items,
        definitions=MAILBOX_CATALOG_CONTRACT.get("status_definitions") or [],
        value_key="status",
        matches=_matches_status,
    )


def _read_capability_facets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _fixed_definition_facets(
        items,
        definitions=MAILBOX_CATALOG_CONTRACT.get("read_capability_definitions") or [],
        value_key="read_capability",
        matches=_matches_read_capability,
    )


def _action_facets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _fixed_definition_facets(
        items,
        definitions=MAILBOX_CATALOG_CONTRACT.get("action_definitions") or [],
        value_key="action",
        matches=_matches_action,
    )


def _parse_timestamp(raw_value: str) -> float | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).timestamp()


def _timestamp_sort_key(item: dict[str, Any], key: str) -> tuple[int, float, str]:
    raw_value = str((item.get("timestamps") or {}).get(key) or "").strip()
    if not raw_value:
        return (0, 0.0, "")
    parsed_value = _parse_timestamp(raw_value)
    return (1, parsed_value if parsed_value is not None else 0.0, raw_value)


def _stable_item_key(item: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(item.get("kind") or ""),
        str(item.get("email") or "").lower(),
        int(item.get("source_id") or 0),
        str(item.get("id") or ""),
    )


def _sort_mailboxes(items: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    stable_items = sorted(items, key=_stable_item_key)
    if sort == "updated_desc":
        return sorted(stable_items, key=lambda item: _timestamp_sort_key(item, "updated_at"), reverse=True)
    if sort == "created_desc":
        return sorted(stable_items, key=lambda item: _timestamp_sort_key(item, "created_at"), reverse=True)
    if sort == "email_asc":
        return sorted(stable_items, key=lambda item: str(item.get("email") or "").lower())
    if sort == "provider_asc":
        return sorted(
            stable_items,
            key=lambda item: (
                str(item.get("provider_label") or item.get("provider") or "").lower(),
                str(item.get("provider") or "").lower(),
                str(item.get("email") or "").lower(),
            ),
        )
    if sort == "status_asc":
        return sorted(
            stable_items,
            key=lambda item: (
                str(item.get("status") or "").lower(),
                str(item.get("pool_status") or "").lower(),
                str(item.get("provider") or "").lower(),
                str(item.get("email") or "").lower(),
            ),
        )
    return stable_items


def _summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {str(field["key"]): 0 for field in MAILBOX_SUMMARY_FIELDS}
    summary["total"] = len(items)
    kind_summary_fields = {
        str(field.get("kind") or "").strip().lower(): str(field.get("key") or "")
        for field in MAILBOX_SUMMARY_FIELDS
        if field.get("source") == "kind"
    }
    status_summary_fields = [
        (str(field.get("key") or ""), {str(status or "").strip().lower() for status in (field.get("statuses") or [])})
        for field in MAILBOX_SUMMARY_FIELDS
        if field.get("source") == "status"
    ]
    pool_summary_fields = [
        str(field.get("key") or "") for field in MAILBOX_SUMMARY_FIELDS if field.get("source") == "pool_status"
    ]
    for item in items:
        kind = str(item.get("kind") or "").strip().lower()
        status = str(item.get("status") or "").lower()
        summary_key = kind_summary_fields.get(kind)
        if summary_key:
            summary[summary_key] += 1
        for status_summary_key, statuses in status_summary_fields:
            if status_summary_key and status in statuses:
                summary[status_summary_key] += 1
        if str(item.get("pool_status") or ""):
            for pool_summary_key in pool_summary_fields:
                if pool_summary_key:
                    summary[pool_summary_key] += 1
    return summary


def list_unified_mailboxes(
    *,
    kind: str = "all",
    status: str = "all",
    read_capability: str = "all",
    action: str = "all",
    provider: str = "all",
    search: str = "",
    sort: str = "updated_desc",
    page: int | str = 1,
    page_size: int | str = 50,
    allowed_account_emails: list[str] | None = None,
) -> dict[str, Any]:
    normalized_kind = _normalize_filter(kind, default="all")
    normalized_status = _normalize_filter(status, default="all")
    normalized_read_capability = _normalize_filter(read_capability, default="all")
    normalized_action = _normalize_filter(action, default="all")
    normalized_provider = _normalize_filter(provider, default="all")
    normalized_sort = _normalize_filter(sort, default="updated_desc")
    if normalized_kind not in _VALID_KIND_FILTERS:
        raise MailboxCatalogError(
            "MAILBOX_KIND_INVALID",
            "邮箱类型筛选无效",
            data={"kind": normalized_kind, "allowed": sorted(_VALID_KIND_FILTERS)},
        )
    if normalized_status not in _VALID_STATUS_FILTERS:
        raise MailboxCatalogError(
            "MAILBOX_STATUS_INVALID",
            "邮箱状态筛选无效",
            data={"status": normalized_status, "allowed": sorted(_VALID_STATUS_FILTERS)},
        )
    if normalized_read_capability not in _VALID_READ_CAPABILITY_FILTERS:
        raise MailboxCatalogError(
            "MAILBOX_READ_CAPABILITY_INVALID",
            "邮箱读取方式筛选无效",
            data={"read_capability": normalized_read_capability, "allowed": sorted(_VALID_READ_CAPABILITY_FILTERS)},
        )
    if normalized_action not in _VALID_ACTION_FILTERS:
        raise MailboxCatalogError(
            "MAILBOX_ACTION_INVALID",
            "邮箱能力筛选无效",
            data={"action": normalized_action, "allowed": sorted(_VALID_ACTION_FILTERS)},
        )
    if normalized_sort not in _VALID_SORT_FILTERS:
        raise MailboxCatalogError(
            "MAILBOX_SORT_INVALID",
            "邮箱排序方式无效",
            data={"sort": normalized_sort, "allowed": sorted(_VALID_SORT_FILTERS)},
        )

    normalized_page = _coerce_bounded_int(page, default=1)
    normalized_page_size = _coerce_bounded_int(page_size, default=50, maximum=200)
    items = _apply_account_email_scope(_load_mailboxes_from_sources(), allowed_account_emails)
    kind_context_filtered = _apply_provider_filter(
        _apply_context_filters(
            items,
            kind="all",
            status=normalized_status,
            read_capability=normalized_read_capability,
            action=normalized_action,
            search=search,
        ),
        normalized_provider,
    )
    status_context_filtered = _apply_provider_filter(
        _apply_context_filters(
            items,
            kind=normalized_kind,
            status="all",
            read_capability=normalized_read_capability,
            action=normalized_action,
            search=search,
        ),
        normalized_provider,
    )
    read_capability_context_filtered = _apply_provider_filter(
        _apply_context_filters(
            items,
            kind=normalized_kind,
            status=normalized_status,
            read_capability="all",
            action=normalized_action,
            search=search,
        ),
        normalized_provider,
    )
    action_context_filtered = _apply_provider_filter(
        _apply_context_filters(
            items,
            kind=normalized_kind,
            status=normalized_status,
            read_capability=normalized_read_capability,
            action="all",
            search=search,
        ),
        normalized_provider,
    )
    context_filtered = _apply_context_filters(
        items,
        kind=normalized_kind,
        status=normalized_status,
        read_capability=normalized_read_capability,
        action=normalized_action,
        search=search,
    )
    filtered = _sort_mailboxes(_apply_provider_filter(context_filtered, normalized_provider), normalized_sort)
    mailbox_inventory = _mailbox_provider_inventory(filtered)
    total_count = len(filtered)
    total_pages = (total_count + normalized_page_size - 1) // normalized_page_size if total_count else 0
    effective_page = min(normalized_page, total_pages) if total_pages else 1
    offset = (effective_page - 1) * normalized_page_size
    page_items = filtered[offset : offset + normalized_page_size]

    return {
        "success": True,
        "mailboxes": page_items,
        "summary": _summary(filtered),
        "facets": {
            "kinds": _kind_facets(kind_context_filtered),
            "statuses": _status_facets(status_context_filtered),
            "read_capabilities": _read_capability_facets(read_capability_context_filtered),
            "providers": _provider_facets(context_filtered),
            "actions": _action_facets(action_context_filtered),
        },
        "pagination": {
            "page": effective_page,
            "page_size": normalized_page_size,
            "total_count": total_count,
            "total_pages": total_pages,
        },
        "filters": {
            "kind": normalized_kind,
            "status": normalized_status,
            "read_capability": normalized_read_capability,
            "action": normalized_action,
            "provider": normalized_provider,
            "search": str(search or ""),
            "sort": normalized_sort,
        },
        "provider_context": get_mailbox_directory_provider_context(mailbox_inventory=mailbox_inventory),
        "contract": copy.deepcopy(MAILBOX_CATALOG_CONTRACT),
    }
