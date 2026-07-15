from __future__ import annotations

import copy
from typing import Any

from outlook_web import __version__ as APP_VERSION
from outlook_web.services.external_request_limits import (
    CALLER_ID_MAX_LEN,
    DETAIL_MAX_LEN,
    EMAIL_DOMAIN_MAX_LEN,
    PROJECT_KEY_MAX_LEN,
    REASON_MAX_LEN,
    TASK_ID_MAX_LEN,
    TASK_MAILBOX_PREFIX_MAX_LEN,
)
from outlook_web.services.mailbox_directory_contract import get_mailbox_catalog_contract
from outlook_web.services.provider_catalog import EXTERNAL_API_V1_PREFIX, get_external_api_capabilities_contract
from outlook_web.services.pool import VALID_RESULTS

from .paths import _paths
from .schemas import _schemas

def get_external_api_openapi_contract(*, consumer: dict[str, Any] | None = None) -> dict[str, Any]:
    capabilities = get_external_api_capabilities_contract(consumer=consumer)
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Outlook Email Plus External API",
            "version": APP_VERSION,
            "description": "Machine-readable contract for API-key protected mailbox, provider, pool, and task temp-mail automation endpoints.",
        },
        "servers": [{"url": "/"}],
        "security": [{"ApiKeyAuth": []}],
        "x-capabilities": copy.deepcopy(capabilities),
        "x-external-api-version": "v1",
        "x-legacy-endpoints": copy.deepcopy(capabilities.get("legacy_endpoints") or {}),
        "x-compatibility": copy.deepcopy(capabilities.get("compatibility") or {}),
        "paths": _paths(capabilities),
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            },
            "schemas": _schemas(capabilities),
        },
    }
