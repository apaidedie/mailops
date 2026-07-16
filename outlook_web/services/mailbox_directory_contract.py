from __future__ import annotations

import copy
from typing import Any

MAILBOX_KIND_DEFINITIONS = [
    {"kind": "account", "label": "普通账号", "label_en": "Accounts", "summary_key": "account"},
    {"kind": "temp", "label": "临时邮箱", "label_en": "Temp mailboxes", "summary_key": "temp"},
]

MAILBOX_KIND_VALUES = [item["kind"] for item in MAILBOX_KIND_DEFINITIONS]
MAILBOX_KIND_FILTERS = ["all", *MAILBOX_KIND_VALUES]
MAILBOX_STATUS_DEFINITIONS = [
    {"status": "active", "label": "可用", "label_en": "Active"},
    {"status": "inactive", "label": "停用", "label_en": "Inactive"},
    {"status": "disabled", "label": "禁用", "label_en": "Disabled"},
    {"status": "finished", "label": "已结束", "label_en": "Finished"},
    {"status": "claimed", "label": "占用中", "label_en": "Claimed"},
    {"status": "available", "label": "池内可用", "label_en": "Available in pool"},
    {"status": "cooldown", "label": "冷却中", "label_en": "Cooling down"},
    {"status": "used", "label": "已使用", "label_en": "Used"},
]
MAILBOX_SORT_DEFINITIONS = [
    {"sort": "updated_desc", "label": "最近更新", "label_en": "Recently updated"},
    {"sort": "created_desc", "label": "创建时间", "label_en": "Created time"},
    {"sort": "email_asc", "label": "邮箱地址", "label_en": "Email address"},
    {"sort": "provider_asc", "label": "来源名称", "label_en": "Provider name"},
    {"sort": "status_asc", "label": "状态", "label_en": "Status"},
]
MAILBOX_READ_CAPABILITY_DEFINITIONS = [
    {"read_capability": "graph", "label": "Microsoft Graph", "label_en": "Microsoft Graph"},
    {"read_capability": "imap", "label": "IMAP", "label_en": "IMAP"},
    {"read_capability": "temp_provider", "label": "临时邮箱 Provider", "label_en": "Temp-mail provider"},
]
MAILBOX_ACTION_DEFINITIONS = [
    {"action": "read_messages", "label": "可读邮件", "label_en": "Read messages"},
    {"action": "refresh_auth", "label": "刷新授权", "label_en": "Refresh auth"},
    {"action": "delete_remote_mailbox", "label": "删除远端邮箱", "label_en": "Delete remote mailbox"},
    {"action": "delete_message", "label": "删除邮件", "label_en": "Delete message"},
    {"action": "clear_messages", "label": "清空邮件", "label_en": "Clear messages"},
]
MAILBOX_STATUS_FILTERS = ["all", *[item["status"] for item in MAILBOX_STATUS_DEFINITIONS]]
MAILBOX_READ_CAPABILITY_FILTERS = ["all", *[item["read_capability"] for item in MAILBOX_READ_CAPABILITY_DEFINITIONS]]
MAILBOX_ACTION_FILTERS = ["all", *[item["action"] for item in MAILBOX_ACTION_DEFINITIONS]]
MAILBOX_SORT_FILTERS = [item["sort"] for item in MAILBOX_SORT_DEFINITIONS]
MAILBOX_SUMMARY_FIELDS = [
    {"key": "total", "label": "总数", "label_en": "Total", "source": "total"},
    *[
        {
            "key": item["summary_key"],
            "label": item["label"],
            "label_en": item["label_en"],
            "source": "kind",
            "kind": item["kind"],
        }
        for item in MAILBOX_KIND_DEFINITIONS
    ],
    {"key": "active", "label": "可用", "label_en": "Active", "source": "status", "statuses": ["active"]},
    {
        "key": "inactive",
        "label": "不可用",
        "label_en": "Inactive",
        "source": "status",
        "statuses": ["inactive", "disabled", "finished"],
    },
    {"key": "pool", "label": "号池", "label_en": "Pool", "source": "pool_status"},
]
MAILBOX_QUICK_VIEW_DEFAULT_FILTERS = {
    "kind": "all",
    "status": "all",
    "read_capability": "all",
    "action": "all",
    "provider": "all",
    "sort": "updated_desc",
    "search": "",
}
MAILBOX_QUICK_VIEW_PRESETS = [
    {
        "key": "all",
        "label": "全部邮箱",
        "label_en": "All mailboxes",
        "description": "完整目录",
        "description_en": "Full directory",
        "filters": {**MAILBOX_QUICK_VIEW_DEFAULT_FILTERS},
    },
    {
        "key": "accounts",
        "label": "普通账号",
        "label_en": "Accounts",
        "description": "Outlook/IMAP",
        "description_en": "Outlook/IMAP",
        "filters": {**MAILBOX_QUICK_VIEW_DEFAULT_FILTERS, "kind": "account"},
    },
    {
        "key": "temp",
        "label": "临时邮箱",
        "label_en": "Temp mailboxes",
        "description": "Provider 邮箱",
        "description_en": "Provider mailboxes",
        "filters": {**MAILBOX_QUICK_VIEW_DEFAULT_FILTERS, "kind": "temp"},
    },
    {
        "key": "readable",
        "label": "可读信",
        "label_en": "Readable",
        "description": "支持读取邮件",
        "description_en": "Supports message reading",
        "filters": {**MAILBOX_QUICK_VIEW_DEFAULT_FILTERS, "action": "read_messages"},
    },
    {
        "key": "attention",
        "label": "需处理",
        "label_en": "Needs attention",
        "description": "停用或不可用",
        "description_en": "Inactive or unavailable",
        "filters": {**MAILBOX_QUICK_VIEW_DEFAULT_FILTERS, "status": "inactive"},
    },
]


def get_mailbox_catalog_contract() -> dict[str, Any]:
    return {
        "version": 1,
        "item_id_format": "{kind}:{source_id}",
        "kinds": list(MAILBOX_KIND_VALUES),
        "kind_definitions": copy.deepcopy(MAILBOX_KIND_DEFINITIONS),
        "status_definitions": copy.deepcopy(MAILBOX_STATUS_DEFINITIONS),
        "read_capability_definitions": copy.deepcopy(MAILBOX_READ_CAPABILITY_DEFINITIONS),
        "action_definitions": copy.deepcopy(MAILBOX_ACTION_DEFINITIONS),
        "sort_definitions": copy.deepcopy(MAILBOX_SORT_DEFINITIONS),
        "summary_fields": copy.deepcopy(MAILBOX_SUMMARY_FIELDS),
        "quick_view_presets": copy.deepcopy(MAILBOX_QUICK_VIEW_PRESETS),
        "read_capabilities": [item["read_capability"] for item in MAILBOX_READ_CAPABILITY_DEFINITIONS],
        "provider_context": {
            "version": 1,
            "source_priority": "provider_context.selection_policy.source_priority",
            "deployment_templates": "provider_context.deployment_profile.templates",
        },
        "action_contract": {
            "version": 1,
            "external_read_contract": "provider_catalog.get_external_mailbox_read_contract(lifecycle=none)",
            "item_query": "action_contract.external.*.query.email",
            "internal_open_target": "action_contract.internal.open_mailbox",
        },
        "filters": {
            "kind": list(MAILBOX_KIND_FILTERS),
            "status": list(MAILBOX_STATUS_FILTERS),
            "read_capability": list(MAILBOX_READ_CAPABILITY_FILTERS),
            "action": list(MAILBOX_ACTION_FILTERS),
            "provider": "all_or_provider_key",
            "sort": list(MAILBOX_SORT_FILTERS),
        },
    }
