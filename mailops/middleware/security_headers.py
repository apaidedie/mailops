"""Baseline browser security headers for all Flask responses."""

from __future__ import annotations

from flask import request

from mailops import config

BASE_CSP_DIRECTIVES = (
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self' 'unsafe-inline'",
    "connect-src 'self'",
    "font-src 'self' data:",
    "form-action 'self'",
)
UPGRADE_INSECURE_REQUESTS_DIRECTIVE = "upgrade-insecure-requests"
PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
)


def _should_emit_hsts() -> bool:
    return bool(request.is_secure or config.get_security_headers_force_hsts())


def build_content_security_policy(*, upgrade_insecure_requests: bool = False) -> str:
    directives = list(BASE_CSP_DIRECTIVES)
    if upgrade_insecure_requests:
        directives.append(UPGRADE_INSECURE_REQUESTS_DIRECTIVE)
    return "; ".join(directives)


def build_hsts_header() -> str:
    return f"max-age={config.get_security_hsts_max_age()}; includeSubDomains"


def attach_security_headers(response):
    """Attach a conservative security-header baseline without overwriting route headers."""
    if not config.get_security_headers_enabled():
        return response

    emit_hsts = _should_emit_hsts()
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
    response.headers.setdefault("Content-Security-Policy", build_content_security_policy(upgrade_insecure_requests=emit_hsts))
    if emit_hsts:
        response.headers.setdefault("Strict-Transport-Security", build_hsts_header())
    return response
