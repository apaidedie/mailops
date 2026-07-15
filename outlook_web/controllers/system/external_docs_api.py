from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Response, jsonify, request

from outlook_web import __version__ as APP_VERSION
from outlook_web import config
from outlook_web.db import (
    DB_SCHEMA_LAST_UPGRADE_ERROR_KEY,
    DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY,
    DB_SCHEMA_VERSION,
    DB_SCHEMA_VERSION_KEY,
    create_sqlite_connection,
)
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.security.auth import api_key_required, get_external_api_consumer, login_required
from outlook_web.security.external_api_guard import external_api_guards
from outlook_web.services import external_api as external_api_service
from outlook_web.services import mailbox_resolver
from outlook_web.services.external_api_docs import render_external_api_docs_html
from outlook_web.services.external_api_openapi import get_external_api_openapi_contract
from outlook_web.services.provider_catalog import (
    get_external_api_capabilities_contract,
    get_external_api_integration_bundle,
    get_external_mailbox_read_contract,
    get_external_api_readiness_summary,
    temp_mail_provider_label,
)
from outlook_web.services.scheduler import REFRESH_LOCK_NAME

@api_key_required
@external_api_guards()
def api_external_capabilities() -> Any:
    """对外能力说明接口"""
    consumer = get_external_api_consumer() or {}
    data = {
        "service": "outlook-email-plus",
        "version": APP_VERSION,
        **get_external_api_capabilities_contract(consumer=consumer),
    }
    external_api_service.audit_external_api_access(
        action="external_api_access",
        email_addr="",
        endpoint="/api/v1/external/capabilities",
        status="ok",
        details={
            "feature_count": len(data["features"]),
            "restricted_count": len(data["restricted_features"]),
            "pool_external_enabled": data["pool"]["external_enabled"],
            "pool_consumer_has_access": data["pool"]["current_consumer_has_access"],
        },
    )
    return jsonify(external_api_service.ok(data))

@api_key_required
@external_api_guards()
def api_external_integration_bundle() -> Any:
    """One-stop readiness bundle for external integration clients."""
    consumer = get_external_api_consumer() or {}
    conn = create_sqlite_connection()
    try:
        db_ok = True
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception:
            db_ok = False
        openapi_contract = get_external_api_openapi_contract(consumer=consumer)
        data = get_external_api_integration_bundle(
            consumer=consumer,
            service="outlook-email-plus",
            version=APP_VERSION,
            database_ok=db_ok,
            upstream_probe_ok=None,
            openapi_metadata=openapi_contract,
        )
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr="",
            endpoint="/api/v1/external/integration-bundle",
            status="ok",
            details={
                "bundle_status": data.get("status"),
                "path_count": (data.get("openapi") or {}).get("path_count"),
                "recommendation_count": len(data.get("recommendations") or []),
            },
        )
        return jsonify(external_api_service.ok(data))
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr="",
            endpoint="/api/v1/external/integration-bundle",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500
    finally:
        conn.close()

@api_key_required
@external_api_guards()
def api_external_openapi() -> Any:
    """Machine-readable contract for external API clients."""
    consumer = get_external_api_consumer() or {}
    data = get_external_api_openapi_contract(consumer=consumer)
    external_api_service.audit_external_api_access(
        action="external_api_access",
        email_addr="",
        endpoint="/api/v1/external/openapi.json",
        status="ok",
        details={
            "path_count": len(data.get("paths") or {}),
            "schema_count": len((data.get("components") or {}).get("schemas") or {}),
        },
    )
    return jsonify(data)

@api_key_required
@external_api_guards()
def api_external_docs() -> Any:
    """Browser-readable external API documentation generated from OpenAPI."""
    consumer = get_external_api_consumer() or {}
    html = render_external_api_docs_html(consumer=consumer)
    external_api_service.audit_external_api_access(
        action="external_api_access",
        email_addr="",
        endpoint="/api/v1/external/docs",
        status="ok",
        details={"format": "html", "consumer_is_legacy": bool(consumer.get("is_legacy"))},
    )
    return Response(html, mimetype="text/html; charset=utf-8")

@api_key_required
@external_api_guards()
def api_external_account_status() -> Any:
    """对外账号状态检查"""
    email_addr = (request.args.get("email") or "").strip()
    if not email_addr or "@" not in email_addr:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=email_addr,
            endpoint="/api/v1/external/account-status",
            status="error",
            details={"code": "INVALID_PARAM"},
        )
        return jsonify(external_api_service.fail("INVALID_PARAM", "email 参数不合法")), 400
    try:
        external_api_service.ensure_external_email_scope(email_addr, allow_finished=True)
    except external_api_service.ExternalApiError as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=email_addr,
            endpoint="/api/v1/external/account-status",
            status="error",
            details={"code": exc.code},
        )
        return jsonify(external_api_service.fail(exc.code, exc.message, data=exc.data)), exc.status

    mailbox = mailbox_resolver.resolve_mailbox(email_addr)
    if mailbox.get("kind") == "temp":
        status = str(mailbox.get("status") or "active").strip().lower() or "active"
        provider_name = str(mailbox.get("provider_name") or mailbox.get("source") or "").strip()
        data = {
            "email": email_addr,
            "exists": True,
            "kind": "temp",
            "mailbox_type": str(mailbox.get("mailbox_type") or "user"),
            "provider": provider_name,
            "provider_name": provider_name,
            "provider_label": temp_mail_provider_label(provider_name),
            "email_domain": str(mailbox.get("domain") or ""),
            "status": status,
            "task_token": str(mailbox.get("task_token") or ""),
            "visible_in_ui": bool(mailbox.get("visible_in_ui")),
            "read_capability": str(mailbox.get("read_capability") or "temp_provider"),
            "preferred_method": "temp_provider",
            "can_read": status == "active",
            "upstream_probe_ok": None,
            "probe_method": "",
            "last_probe_at": "",
            "last_probe_error": "",
            "external_mailbox_read_contract": get_external_mailbox_read_contract(lifecycle="none"),
        }
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=email_addr,
            endpoint="/api/v1/external/account-status",
            status="ok",
            details={
                "kind": "temp",
                "provider": provider_name,
                "can_read": data["can_read"],
                "upstream_probe_ok": None,
            },
        )
        return jsonify(external_api_service.ok(data))

    account = accounts_repo.get_account_by_email(email_addr)
    if not account:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=email_addr,
            endpoint="/api/v1/external/account-status",
            status="error",
            details={"code": "ACCOUNT_NOT_FOUND"},
        )
        return jsonify(external_api_service.fail("ACCOUNT_NOT_FOUND", "账号不存在", data={"email": email_addr})), 404

    account_type = (account.get("account_type") or "outlook").strip().lower()
    provider = (account.get("provider") or account_type or "outlook").strip().lower()
    preferred_method = "imap_generic" if account_type == "imap" else "graph"
    can_read = external_api_service.can_account_read(account)

    data = {
        "email": email_addr,
        "exists": True,
        "kind": "account",
        "account_type": account_type,
        "provider": provider,
        "email_domain": account.get("email_domain") or "",
        "group_id": account.get("group_id"),
        "status": account.get("status"),
        "last_refresh_at": account.get("last_refresh_at"),
        "preferred_method": preferred_method,
        "can_read": can_read,
        "upstream_probe_ok": None,
        "probe_method": "",
        "last_probe_at": "",
        "last_probe_error": "",
        "external_mailbox_read_contract": get_external_mailbox_read_contract(lifecycle="none"),
    }
    if can_read:
        probe_summary = external_api_service.probe_account_upstream(account)
        data["upstream_probe_ok"] = probe_summary.get("upstream_probe_ok")
        data["probe_method"] = probe_summary.get("probe_method") or preferred_method
        data["last_probe_at"] = probe_summary.get("last_probe_at") or ""
        data["last_probe_error"] = probe_summary.get("last_probe_error") or ""
    external_api_service.audit_external_api_access(
        action="external_api_access",
        email_addr=email_addr,
        endpoint="/api/v1/external/account-status",
        status="ok",
        details={
            "kind": "account",
            "preferred_method": preferred_method,
            "can_read": can_read,
            "upstream_probe_ok": data["upstream_probe_ok"],
        },
    )
    return jsonify(external_api_service.ok(data))
