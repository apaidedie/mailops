from __future__ import annotations

import re
from typing import Callable, Iterable, Optional

from flask import Blueprint

# Historical prefix removed in W2; kept only for migration messaging / documentation.
REMOVED_LEGACY_EXTERNAL_API_PREFIX = "/api/external"
VERSIONED_EXTERNAL_API_PREFIX = "/api/v1/external"


def external_api_path(path: str) -> str:
    """Normalize an external API path or suffix to the canonical v1 path."""

    normalized = path.strip()
    if normalized.startswith(VERSIONED_EXTERNAL_API_PREFIX):
        return normalized
    if normalized.startswith(REMOVED_LEGACY_EXTERNAL_API_PREFIX):
        suffix = normalized.removeprefix(REMOVED_LEGACY_EXTERNAL_API_PREFIX)
        return f"{VERSIONED_EXTERNAL_API_PREFIX}{suffix}"
    suffix = normalized if normalized.startswith("/") else f"/{normalized}"
    return f"{VERSIONED_EXTERNAL_API_PREFIX}{suffix}"


def external_api_paths(path: str) -> tuple[str, str]:
    """Compatibility shim: return (canonical, canonical).

    Historically returned (legacy, v1). Legacy routes are removed; callers that
    still unpack a pair receive the canonical path twice.
    """

    canonical = external_api_path(path)
    return canonical, canonical


def add_external_api_url_rule(
    bp: Blueprint,
    path: str,
    *,
    view_func: Callable,
    methods: Iterable[str],
    endpoint: str | None = None,
    csrf_exempt: Optional[Callable] = None,
) -> None:
    """Register one external API handler on the canonical `/api/v1/external/*` path only."""

    versioned_path = external_api_path(path)
    wrapped_view = csrf_exempt(view_func) if csrf_exempt else view_func
    endpoint_base = endpoint or _endpoint_name(path, view_func)
    bp.add_url_rule(
        versioned_path,
        endpoint=f"{endpoint_base}_v1",
        view_func=wrapped_view,
        methods=list(methods),
    )


def _endpoint_name(path: str, view_func: Callable) -> str:
    name = getattr(view_func, "__name__", "external_api")
    suffix = re.sub(r"[^a-zA-Z0-9_]+", "_", path.strip("/"))
    suffix = suffix.strip("_") or "root"
    return f"{name}_{suffix}"
