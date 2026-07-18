from __future__ import annotations

import re
from typing import Any

from flask import Flask
from flask_cors import CORS

from mailops import config

EXTERNAL_API_CORS_METHODS = ("GET", "POST", "OPTIONS")
EXTERNAL_API_CORS_ALLOWED_HEADERS = ("Content-Type", "X-API-Key", "X-Request-Id", "X-Trace-Id")
EXTERNAL_API_CORS_EXPOSED_HEADERS = ("X-Trace-Id",)
EXTERNAL_API_CORS_MAX_AGE_SECONDS = 600
EXTERNAL_API_CORS_RESOURCES = (r"/api/v1/external/*",)
CHROME_EXTENSION_ORIGIN_PATTERN = re.compile(r"^chrome-extension://.*$")


def get_external_api_cors_contract() -> dict[str, Any]:
    origin_config = config.get_external_api_cors_origin_config()
    allowed_origins = list(origin_config.get("origins") or [])
    chrome_extension_enabled = config.get_external_api_cors_allow_chrome_extension()
    invalid_origin_count = int(origin_config.get("invalid_origin_count") or 0)
    if allowed_origins and chrome_extension_enabled:
        mode = "allowlist_and_extension"
        status = "configured"
    elif allowed_origins:
        mode = "allowlist"
        status = "configured"
    elif chrome_extension_enabled:
        mode = "extension_only"
        status = "extension_only"
    else:
        mode = "disabled"
        status = "invalid" if invalid_origin_count else "disabled"
    return {
        "status": status,
        "enabled": bool(allowed_origins or chrome_extension_enabled),
        "mode": mode,
        "allowed_origins": allowed_origins,
        "allowed_origin_count": len(allowed_origins),
        "invalid_origin_count": invalid_origin_count,
        "chrome_extension_enabled": chrome_extension_enabled,
        "credentials": False,
        "methods": list(EXTERNAL_API_CORS_METHODS),
        "allowed_headers": list(EXTERNAL_API_CORS_ALLOWED_HEADERS),
        "exposed_headers": list(EXTERNAL_API_CORS_EXPOSED_HEADERS),
        "max_age_seconds": EXTERNAL_API_CORS_MAX_AGE_SECONDS,
        "environment": {
            "origins": "EXTERNAL_API_CORS_ORIGINS",
            "chrome_extension": "EXTERNAL_API_CORS_ALLOW_CHROME_EXTENSION",
        },
    }


def configure_external_api_cors(app: Flask) -> dict[str, Any]:
    contract = get_external_api_cors_contract()
    app.extensions["external_api_cors"] = contract
    origins: list[Any] = list(contract["allowed_origins"])
    if contract["chrome_extension_enabled"]:
        origins.append(CHROME_EXTENSION_ORIGIN_PATTERN)
    if not origins:
        return contract
    options = {
        "origins": origins,
        "methods": list(EXTERNAL_API_CORS_METHODS),
        "allow_headers": list(EXTERNAL_API_CORS_ALLOWED_HEADERS),
        "expose_headers": list(EXTERNAL_API_CORS_EXPOSED_HEADERS),
        "supports_credentials": False,
        "max_age": EXTERNAL_API_CORS_MAX_AGE_SECONDS,
        "vary_header": True,
    }
    CORS(app, resources={resource: options for resource in EXTERNAL_API_CORS_RESOURCES})
    return contract
