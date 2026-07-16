from __future__ import annotations

import copy
from typing import Any

# Prefix constants (single source for path helpers in this module).
EXTERNAL_API_LEGACY_PREFIX = "/api/external"  # removed in W2; migration reference only
EXTERNAL_API_V1_PREFIX = "/api/v1/external"


def _external_api_path(suffix: str, *, versioned: bool = True) -> str:
    prefix = EXTERNAL_API_V1_PREFIX if versioned else EXTERNAL_API_LEGACY_PREFIX
    normalized = suffix if suffix.startswith("/") else f"/{suffix}"
    return f"{prefix}{normalized}"


def _external_api_endpoint_map(*, versioned: bool = True) -> dict[str, str]:
    return {
        "health": _external_api_path("/health", versioned=versioned),
        "capabilities": _external_api_path("/capabilities", versioned=versioned),
        "integration_bundle": _external_api_path("/integration-bundle", versioned=versioned),
        "docs": _external_api_path("/docs", versioned=versioned),
        "openapi": _external_api_path("/openapi.json", versioned=versioned),
        "mailboxes": _external_api_path("/mailboxes", versioned=versioned),
        "providers": _external_api_path("/providers", versioned=versioned),
        "provider_health": _external_api_path("/providers/{kind}/{provider}/health", versioned=versioned),
        "provider_preflight": _external_api_path("/providers/preflight", versioned=versioned),
        "mailbox_session_start": _external_api_path("/mailbox-sessions/start", versioned=versioned),
        "mailbox_session_read": _external_api_path("/mailbox-sessions/read", versioned=versioned),
        "mailbox_session_close": _external_api_path("/mailbox-sessions/close", versioned=versioned),
        "account_status": _external_api_path("/account-status", versioned=versioned),
        "messages": _external_api_path("/messages", versioned=versioned),
        "latest_message": _external_api_path("/messages/latest", versioned=versioned),
        "message_detail": _external_api_path("/messages/{message_id}", versioned=versioned),
        "message_raw": _external_api_path("/messages/{message_id}/raw", versioned=versioned),
        "verification_code": _external_api_path("/verification-code", versioned=versioned),
        "verification_link": _external_api_path("/verification-link", versioned=versioned),
        "wait_message": _external_api_path("/wait-message", versioned=versioned),
        "probe_status": _external_api_path("/probe/{probe_id}", versioned=versioned),
        "pool_claim_random": _external_api_path("/pool/claim-random", versioned=versioned),
        "pool_claim_release": _external_api_path("/pool/claim-release", versioned=versioned),
        "pool_claim_complete": _external_api_path("/pool/claim-complete", versioned=versioned),
        "pool_stats": _external_api_path("/pool/stats", versioned=versioned),
        "temp_mail_apply": _external_api_path("/temp-emails/apply", versioned=versioned),
        "temp_mail_finish": _external_api_path("/temp-emails/{task_token}/finish", versioned=versioned),
    }


def get_external_api_endpoint_map() -> dict[str, str]:
    """Return canonical versioned external API endpoint paths."""

    return _external_api_endpoint_map(versioned=True)


def get_external_api_legacy_endpoint_map() -> dict[str, str]:
    """Legacy map removed in W2 — always empty.

    Kept as a callable so older imports/tests can resolve the symbol; callers
    must treat an empty map as “legacy not supported”.
    """

    return {}


def get_external_api_compatibility_contract() -> dict[str, Any]:
    return {
        "canonical_prefix": EXTERNAL_API_V1_PREFIX,
        "legacy_prefix": EXTERNAL_API_LEGACY_PREFIX,
        "legacy_supported": False,
        "legacy_endpoints": {},
        "aliases": {},
        "removed_legacy_prefix": EXTERNAL_API_LEGACY_PREFIX,
        "migration_doc": "docs/migration/remove-legacy-external-api.md",
    }


_CANONICAL_EXTERNAL_ENDPOINTS = get_external_api_endpoint_map()
_LEGACY_EXTERNAL_ENDPOINTS: dict[str, str] = {}
PROVIDER_HEALTH_ENDPOINT = _CANONICAL_EXTERNAL_ENDPOINTS["provider_health"]
PROVIDER_PREFLIGHT_ENDPOINT = _CANONICAL_EXTERNAL_ENDPOINTS["provider_preflight"]
# Historical names retained for import compatibility; values are canonical v1 paths.
LEGACY_PROVIDER_HEALTH_ENDPOINT = PROVIDER_HEALTH_ENDPOINT
LEGACY_PROVIDER_PREFLIGHT_ENDPOINT = PROVIDER_PREFLIGHT_ENDPOINT


def get_provider_documentation_contract() -> dict[str, Any]:
    """Return secret-free documentation pointers for provider onboarding."""
    return {
        "version": 1,
        "recommended_human_start": "provider_onboarding",
        "recommended_machine_start": "openapi",
        "entries": {
            "provider_onboarding": {
                "label": "Provider onboarding guide",
                "type": "guide",
                "path": "docs/provider-onboarding.md",
                "purpose": "Human-readable first-run path for external API discovery, provider selection, and future provider extension.",
            },
            "external_integration_quickstart": {
                "label": "External integration quickstart",
                "type": "guide",
                "path": "docs/external-integration-quickstart.md",
                "purpose": "Short path for registration workers and third-party services to validate discovery contracts and start mailbox sessions.",
            },
            "plugin_extension": {
                "label": "Temp-mail provider plugin guide",
                "type": "guide",
                "path": "docs/temp-mail-provider-plugin-guide.md",
                "purpose": "Implementation contract for adding a new temp-mail provider plugin without changing core routes.",
            },
            "plugin_prompt": {
                "label": "Temp-mail provider implementation prompt",
                "type": "agent_prompt",
                "path": "docs/temp-mail-provider-plugin-prompt.md",
                "purpose": "Agent-ready prompt for implementing one concrete provider from upstream API documentation.",
            },
            "env_example": {
                "label": ".env example",
                "type": "example",
                "path": ".env.example",
                "purpose": "Environment-variable template for runtime provider selection and provider credentials.",
            },
            "provider_config_json": {
                "label": "Provider config JSON example",
                "type": "example",
                "path": ".runtime/providers.example.json",
                "purpose": "Provider-selection config-file example for JSON deployments.",
            },
            "provider_config_toml": {
                "label": "Provider config TOML example",
                "type": "example",
                "path": ".runtime/providers.example.toml",
                "purpose": "Provider-selection config-file example for TOML deployments.",
            },
            "openapi": {
                "label": "External API OpenAPI contract",
                "type": "api_contract",
                "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["openapi"],
                "purpose": "Machine-readable API contract for external clients and generated integrations.",
            },
            "api_docs": {
                "label": "External API documentation page",
                "type": "api_docs",
                "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["docs"],
                "purpose": "Authenticated browser-readable documentation for external API discovery, provider selection, and mailbox-session workflows.",
            },
        },
    }


EXTERNAL_READ_ENDPOINTS = {
    key: _CANONICAL_EXTERNAL_ENDPOINTS[key]
    for key in (
        "messages",
        "latest_message",
        "message_detail",
        "message_raw",
        "verification_code",
        "verification_link",
        "wait_message",
        "probe_status",
        "account_status",
    )
}
MAILBOX_SESSION_START_ENDPOINT = _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_start"]
MAILBOX_SESSION_READ_ENDPOINT = _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_read"]
MAILBOX_SESSION_CLOSE_ENDPOINT = _CANONICAL_EXTERNAL_ENDPOINTS["mailbox_session_close"]

EXTERNAL_READ_QUERY_FIELDS = [
    "email",
    "claim_token",
    "folder",
    "skip",
    "top",
    "from_contains",
    "subject_contains",
    "since_minutes",
]

_EXTERNAL_READ_ACTIONS = {
    "read_messages": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["messages"],
        "query_fields": EXTERNAL_READ_QUERY_FIELDS,
    },
    "read_latest_message": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["latest_message"],
        "query_fields": [
            "email",
            "claim_token",
            "folder",
            "from_contains",
            "subject_contains",
            "since_minutes",
        ],
    },
    "read_message_detail": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["message_detail"],
        "path_fields": ["message_id"],
        "query_fields": ["email", "claim_token", "folder"],
    },
    "read_message_raw": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["message_raw"],
        "path_fields": ["message_id"],
        "query_fields": ["email", "claim_token", "folder"],
    },
    "read_verification_code": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["verification_code"],
        "query_fields": [
            "email",
            "claim_token",
            "folder",
            "from_contains",
            "subject_contains",
            "since_minutes",
            "code_length",
            "code_regex",
            "code_source",
        ],
    },
    "read_verification_link": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["verification_link"],
        "query_fields": ["email", "claim_token", "folder", "from_contains", "subject_contains", "since_minutes"],
    },
    "wait_message_async": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["wait_message"],
        "fixed_query": {"mode": "async"},
        "query_fields": [
            "email",
            "claim_token",
            "folder",
            "from_contains",
            "subject_contains",
            "since_minutes",
            "timeout_seconds",
            "poll_interval",
            "mode",
        ],
    },
    "poll_probe": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["probe_status"],
        "path_fields": ["probe_id"],
    },
    "check_status": {
        "method": "GET",
        "endpoint": EXTERNAL_READ_ENDPOINTS["account_status"],
        "query_fields": ["email"],
    },
}

_EXTERNAL_POOL_LIFECYCLE_ACTIONS = {
    "release_claim": {
        "method": "POST",
        "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_release"],
        "body_fields": ["account_id", "claim_token", "caller_id", "task_id", "reason"],
    },
    "complete_claim": {
        "method": "POST",
        "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["pool_claim_complete"],
        "body_fields": ["account_id", "claim_token", "caller_id", "task_id", "result", "detail"],
    },
}

_EXTERNAL_TASK_TEMP_ACTIONS = {
    "finish_task_mailbox": {
        "method": "POST",
        "endpoint": _CANONICAL_EXTERNAL_ENDPOINTS["temp_mail_finish"],
        "path_fields": ["task_token"],
        "body_fields": ["result", "detail"],
    },
}

_EXTERNAL_MAILBOX_SESSION_CLOSE_ACTION = {
    "close_session": {
        "method": "POST",
        "endpoint": MAILBOX_SESSION_CLOSE_ENDPOINT,
        "body_fields": [
            "session_type",
            "account_id",
            "claim_token",
            "task_token",
            "caller_id",
            "task_id",
            "result",
            "detail",
            "reason",
        ],
    },
}

_EXTERNAL_MAILBOX_SESSION_READ_ACTION = {
    "read_session": {
        "method": "POST",
        "endpoint": MAILBOX_SESSION_READ_ENDPOINT,
        "body_fields": [
            "session_type",
            "read_action",
            "caller_id",
            "task_id",
            "email",
            "claim_token",
            "task_token",
            "message_id",
            "folder",
            "skip",
            "top",
            "from_contains",
            "subject_contains",
            "since_minutes",
            "code_length",
            "code_regex",
            "code_source",
            "timeout_seconds",
            "poll_interval",
            "mode",
        ],
    },
}

_EXTERNAL_ACTION_ENDPOINT_KEYS = {
    "read_messages": "messages",
    "read_latest_message": "latest_message",
    "read_message_detail": "message_detail",
    "read_message_raw": "message_raw",
    "read_verification_code": "verification_code",
    "read_verification_link": "verification_link",
    "wait_message_async": "wait_message",
    "poll_probe": "probe_status",
    "check_status": "account_status",
    "read_session": "mailbox_session_read",
    "close_session": "mailbox_session_close",
    "release_claim": "pool_claim_release",
    "complete_claim": "pool_claim_complete",
    "finish_task_mailbox": "temp_mail_finish",
}


def _action_contract_next_actions_for_endpoint_map(
    *,
    lifecycle: str,
    endpoints: dict[str, str],
) -> dict[str, dict[str, Any]]:
    contract = get_external_mailbox_read_contract(lifecycle=lifecycle)
    next_actions = copy.deepcopy(contract.get("next_actions") or {})
    for action_key, endpoint_key in _EXTERNAL_ACTION_ENDPOINT_KEYS.items():
        if action_key in next_actions and endpoint_key in endpoints:
            next_actions[action_key]["endpoint"] = endpoints[endpoint_key]
    return next_actions


def get_external_mailbox_read_contract(*, lifecycle: str = "none") -> dict[str, Any]:
    """Return the machine-readable contract for external mailbox reads."""
    next_actions = copy.deepcopy(_EXTERNAL_READ_ACTIONS)
    normalized_lifecycle = str(lifecycle or "none").strip().lower()
    if normalized_lifecycle == "pool_claim":
        next_actions.update(copy.deepcopy(_EXTERNAL_MAILBOX_SESSION_READ_ACTION))
        next_actions.update(copy.deepcopy(_EXTERNAL_POOL_LIFECYCLE_ACTIONS))
        next_actions.update(copy.deepcopy(_EXTERNAL_MAILBOX_SESSION_CLOSE_ACTION))
    elif normalized_lifecycle == "task_temp_mailbox":
        next_actions.update(copy.deepcopy(_EXTERNAL_MAILBOX_SESSION_READ_ACTION))
        next_actions.update(copy.deepcopy(_EXTERNAL_TASK_TEMP_ACTIONS))
        next_actions.update(copy.deepcopy(_EXTERNAL_MAILBOX_SESSION_CLOSE_ACTION))

    return {
        "read_by": ["email", "claim_token"],
        "email_query_field": "email",
        "claim_token_query_field": "claim_token",
        "read_endpoints": copy.deepcopy(EXTERNAL_READ_ENDPOINTS),
        "read_query_fields": list(EXTERNAL_READ_QUERY_FIELDS),
        "next_actions": next_actions,
    }
