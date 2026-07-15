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

def _envelope_ref(schema_ref: str) -> dict[str, Any]:
    return {
        "allOf": [
            {"$ref": "#/components/schemas/ExternalEnvelope"},
            {
                "type": "object",
                "properties": {
                    "data": {"$ref": schema_ref},
                },
            },
        ],
    }

def _json_response(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "200": {
            "description": "Successful response",
            "content": {"application/json": {"schema": schema}},
        },
    }

def _error_responses() -> dict[str, Any]:
    return {
        "400": {"description": "Invalid request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExternalEnvelope"}}}},
        "401": {"description": "Missing or invalid API key", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExternalEnvelope"}}}},
        "403": {"description": "Forbidden", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExternalEnvelope"}}}},
        "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExternalEnvelope"}}}},
        "429": {"description": "Rate limited", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExternalEnvelope"}}}},
        "500": {"description": "Server error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExternalEnvelope"}}}},
    }

def _query_param(name: str, schema: dict[str, Any], *, required: bool = False, description: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "in": "query",
        "required": required,
        "schema": schema,
    }
    if description:
        payload["description"] = description
    return payload

def _path_param(name: str, description: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "schema": {"type": "string"},
        "description": description or name,
    }

def _string_array_schema(values: list[Any] | None = None) -> dict[str, Any]:
    item_schema: dict[str, Any] = {"type": "string"}
    if values is not None:
        item_schema["enum"] = [str(item) for item in values]
    return {"type": "array", "items": item_schema}

def _nullable_string_enum_schema(values: list[Any], *, description: str = "") -> dict[str, Any]:
    enum_values: list[Any] = [None]
    seen = {None}
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        enum_values.append(text)
        seen.add(text)
    schema: dict[str, Any] = {"type": ["string", "null"], "enum": enum_values}
    if description:
        schema["description"] = description
    return schema

def _json_value_schema() -> dict[str, Any]:
    return {"type": ["string", "number", "boolean", "array", "object", "null"]}

def _operation(
    *,
    method: str,
    summary: str,
    operation_id: str,
    response_ref: str,
    parameters: list[dict[str, Any]] | None = None,
    request_schema_ref: str | None = None,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "summary": summary,
        "operationId": operation_id,
        "tags": ["External API"],
        "security": [{"ApiKeyAuth": []}],
        "responses": {
            **_json_response(_envelope_ref(response_ref)),
            **_error_responses(),
        },
    }
    if parameters:
        operation["parameters"] = parameters
    if request_schema_ref:
        operation["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": {"$ref": request_schema_ref}}},
        }
    return {method.lower(): operation}
