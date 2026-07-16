from __future__ import annotations

import copy
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from flask import Response, g, jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.db import get_db
from outlook_web.errors import (
    build_error_payload,
    build_error_response,
    build_export_verify_failure_response,
)
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import groups as groups_repo
from outlook_web.repositories import refresh_logs as refresh_logs_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.repositories import tags as tags_repo
from outlook_web.repositories.distributed_locks import (
    acquire_distributed_lock,
    release_distributed_lock,
)
from outlook_web.repositories.refresh_runs import create_refresh_run, finish_refresh_run
from outlook_web.security.auth import get_client_ip, get_user_agent, login_required
from outlook_web.security.crypto import decrypt_data
from outlook_web.services import graph as graph_service
from outlook_web.services import refresh as refresh_service

from .helpers import _parse_bool_flag


@login_required
def api_get_accounts() -> Any:
    """获取账号列表（支持分页、分组内搜索、标签筛选与排序）"""
    group_id = request.args.get("group_id", type=int)
    page = request.args.get("page", default=1, type=int) or 1
    page_size = request.args.get("page_size", default=50, type=int) or 50
    search = (request.args.get("search", type=str) or "").strip()
    sort_by = (request.args.get("sort_by", type=str) or "refresh_time").strip().lower()
    sort_order = (request.args.get("sort_order", type=str) or "asc").strip().lower()

    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 100))
    if sort_by not in {"refresh_time", "email"}:
        sort_by = "refresh_time"
    if sort_order not in {"asc", "desc"}:
        sort_order = "asc"

    raw_tag_values = request.args.getlist("tag_id")
    raw_tag_values.extend((request.args.get("tag_ids", type=str) or "").split(","))
    tag_ids: List[int] = []
    seen_tag_ids = set()
    for raw_value in raw_tag_values:
        raw_text = str(raw_value or "").strip()
        if not raw_text:
            continue
        try:
            tag_id = int(raw_text)
        except ValueError:
            continue
        if tag_id <= 0 or tag_id in seen_tag_ids:
            continue
        seen_tag_ids.add(tag_id)
        tag_ids.append(tag_id)

    accounts, total_count, effective_page = accounts_repo.load_accounts_page(
        group_id,
        page=page,
        page_size=page_size,
        search=search,
        tag_ids=tag_ids,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    # 获取每个账号的最后刷新状态（批量查询，避免 N+1）
    db = get_db()
    last_log_by_account: Dict[int, Dict[str, Any]] = {}
    try:
        account_ids = [int(a.get("id")) for a in accounts if a.get("id") is not None]
    except Exception:
        account_ids = []

    if account_ids:
        try:
            placeholders = ",".join(["?"] * len(account_ids))
            rows = db.execute(
                f"""
                SELECT l.account_id, l.status, l.error_message, l.created_at
                FROM account_refresh_logs l
                JOIN (
                    SELECT account_id, MAX(id) as max_id
                    FROM account_refresh_logs
                    WHERE account_id IN ({placeholders})
                    GROUP BY account_id
                ) latest
                ON l.account_id = latest.account_id AND l.id = latest.max_id
            """,
                account_ids,
            ).fetchall()
            for r in rows:
                try:
                    last_log_by_account[int(r["account_id"])] = dict(r)
                except Exception:
                    continue
        except Exception:
            last_log_by_account = {}

    # 返回时隐藏敏感信息
    safe_accounts = []
    for acc in accounts:
        acc_id = acc.get("id")
        try:
            acc_id_int = int(acc_id)
        except Exception:
            acc_id_int = None
        last_refresh_log = last_log_by_account.get(acc_id_int) if acc_id_int is not None else None

        safe_accounts.append(
            {
                "id": acc["id"],
                "email": acc["email"],
                "account_type": acc.get("account_type") or "outlook",
                "provider": acc.get("provider") or "outlook",
                "client_id": (acc["client_id"][:8] + "..." if len(acc["client_id"]) > 8 else acc["client_id"]),
                "group_id": acc.get("group_id"),
                "group_name": acc.get("group_name", "默认分组"),
                "group_color": acc.get("group_color", "#666666"),
                "remark": acc.get("remark", ""),
                "status": acc.get("status", "active"),
                "last_refresh_at": acc.get("last_refresh_at", ""),
                "last_refresh_status": (last_refresh_log.get("status") if last_refresh_log else None),
                "last_refresh_error": (last_refresh_log.get("error_message") if last_refresh_log else None),
                "created_at": acc.get("created_at", ""),
                "updated_at": acc.get("updated_at", ""),
                "tags": acc.get("tags", []),
                "telegram_push_enabled": bool(acc.get("telegram_push_enabled")),
                "notification_enabled": bool(acc.get("telegram_push_enabled")),
                "latest_email_subject": acc.get("latest_email_subject", ""),
                "latest_email_from": acc.get("latest_email_from", ""),
                "latest_email_folder": acc.get("latest_email_folder", ""),
                "latest_email_received_at": acc.get("latest_email_received_at", ""),
                "latest_verification_code": acc.get("latest_verification_code", ""),
                "latest_verification_folder": acc.get("latest_verification_folder", ""),
                "latest_verification_received_at": acc.get("latest_verification_received_at", ""),
            }
        )
    return jsonify(
        {
            "success": True,
            "accounts": safe_accounts,
            "pagination": {
                "page": effective_page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        }
    )


@login_required
def api_get_account(account_id: int) -> Any:
    """获取单个账号详情"""
    account = accounts_repo.get_account_by_id(account_id)
    if not account:
        return build_error_response(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            message_en="Account not found",
            status=404,
        )

    return jsonify(
        {
            "success": True,
            "account": {
                "id": account["id"],
                "email": account["email"],
                # 敏感字段默认不回显（避免泄露）；如需查看请走"导出+二次验证"
                "password": "",
                "client_id": account["client_id"],
                "refresh_token": "",
                "has_password": bool(account.get("password")),
                "has_refresh_token": bool(account.get("refresh_token")),
                "group_id": account.get("group_id"),
                "group_name": account.get("group_name", "默认分组"),
                "remark": account.get("remark", ""),
                "status": account.get("status", "active"),
                "account_type": account.get("account_type") or "outlook",
                "provider": account.get("provider") or "outlook",
                "telegram_push_enabled": bool(account.get("telegram_push_enabled")),
                "notification_enabled": bool(account.get("telegram_push_enabled")),
                "latest_email_subject": account.get("latest_email_subject", ""),
                "latest_email_from": account.get("latest_email_from", ""),
                "latest_email_folder": account.get("latest_email_folder", ""),
                "latest_email_received_at": account.get("latest_email_received_at", ""),
                "latest_verification_code": account.get("latest_verification_code", ""),
                "latest_verification_folder": account.get("latest_verification_folder", ""),
                "latest_verification_received_at": account.get("latest_verification_received_at", ""),
                "created_at": account.get("created_at", ""),
                "updated_at": account.get("updated_at", ""),
            },
        }
    )


@login_required
def api_get_providers() -> Any:
    """返回邮箱提供商列表，用于前端下拉选择（PRD-00005 / TDD-00005）"""
    from outlook_web.services.provider_catalog import (
        ACTIVE_MAILBOX_PROVIDER_ENV,
        DEPLOYMENT_ENV_CONTRACT,
        EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
        TEMP_MAIL_PROVIDER_ENV,
        get_active_mailbox_provider_filter_contract,
        get_external_integration_manifest,
        get_external_mailbox_read_contract,
        get_mailbox_provider_catalog,
        get_mailbox_provider_deployment_profile,
        get_mailbox_provider_diagnostics,
        get_mailbox_provider_readiness_summary,
        get_mailbox_provider_selection_policy,
        get_operator_temp_mail_default_provider,
        get_provider_documentation_contract,
        get_provider_integration_guide,
        temp_mail_provider_config_status,
        temp_mail_provider_label,
    )
    from outlook_web.services.providers import get_provider_list

    provider_filter = get_active_mailbox_provider_filter_contract(strict=False)
    deployment_profile = get_mailbox_provider_deployment_profile(strict=False)
    provider_diagnostics = get_mailbox_provider_diagnostics(include_inactive=True)
    selection_policy = get_mailbox_provider_selection_policy(deployment_profile=deployment_profile)
    integration_guide = get_provider_integration_guide(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=provider_diagnostics,
    )
    integration_manifest = get_external_integration_manifest(
        deployment_profile=deployment_profile,
        selection_policy=selection_policy,
        provider_filter=provider_filter,
        provider_diagnostics=provider_diagnostics,
        provider_integration_guide=integration_guide,
    )
    readiness_summary = get_mailbox_provider_readiness_summary(
        provider_diagnostics=provider_diagnostics,
        provider_integration_guide=integration_guide,
        selection_policy=selection_policy,
        discovery={
            "providers_endpoint": "/api/v1/external/providers",
            "provider_health_endpoint": "/api/v1/external/providers/{kind}/{provider}/health",
        },
    )
    # Operator-facing default matches collapsed guide/diagnostics bridge key.
    default_temp_provider = get_operator_temp_mail_default_provider(strict=False)
    default_temp_config = temp_mail_provider_config_status(default_temp_provider)

    return jsonify(
        {
            "success": True,
            "providers": get_provider_list(),
            "mailbox_providers": get_mailbox_provider_catalog(strict=False),
            "provider_diagnostics": provider_diagnostics,
            "provider_filter": provider_filter,
            "active_mailbox_providers": provider_filter["active_providers"],
            "active_mailbox_provider_env": ACTIVE_MAILBOX_PROVIDER_ENV,
            "default_temp_mail_provider": default_temp_provider,
            "default_temp_mail_provider_label": temp_mail_provider_label(default_temp_provider),
            "default_temp_mail_provider_configured": bool(default_temp_config["configured"]),
            "default_temp_mail_provider_missing_config": list(default_temp_config["missing_config"]),
            "default_temp_mail_provider_env": TEMP_MAIL_PROVIDER_ENV,
            "default_pool_claim_provider": settings_repo.get_pool_default_provider(strict=False) or "auto",
            "default_pool_claim_provider_env": EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
            "deployment_env": dict(DEPLOYMENT_ENV_CONTRACT),
            "deployment_profile": deployment_profile,
            "selection_policy": selection_policy,
            "provider_integration_guide": integration_guide,
            "readiness_summary": readiness_summary,
            "integration_manifest": integration_manifest,
            "quickstart": copy.deepcopy(integration_manifest.get("quickstart") or {}),
            "documentation": get_provider_documentation_contract(),
            "external_mailbox_read_contract": get_external_mailbox_read_contract(lifecycle="none"),
        }
    )


@login_required
def api_get_provider_preflight() -> Any:
    """返回全部邮箱来源的批量就绪预检，默认不访问上游网络。"""
    from outlook_web.services.provider_catalog import get_mailbox_provider_preflight

    probe_network = _parse_bool_flag(request.args.get("probe_network"), default=False)
    payload = get_mailbox_provider_preflight(probe_network=probe_network)
    return jsonify({"success": True, "provider_preflight": payload})


@login_required
def api_get_provider_health(kind: str, provider: str) -> Any:
    """返回单个邮箱来源的本地就绪状态，可选执行非破坏性上游探测。"""
    from outlook_web.services.provider_catalog import get_mailbox_provider_health

    probe_network = _parse_bool_flag(request.args.get("probe_network"), default=False)
    payload = get_mailbox_provider_health(kind, provider, probe_network=probe_network)
    if not payload.get("found"):
        return build_error_response(
            "MAILBOX_PROVIDER_NOT_FOUND",
            "邮箱 Provider 不存在",
            message_en="Mailbox provider not found",
            status=404,
            extra={"kind": kind, "provider": provider},
        )
    return jsonify({"success": True, "provider_health": payload})


# ==================== Auto 混合导入 (FD-00006) ====================


@login_required
def api_search_accounts() -> Any:
    """全局搜索账号"""
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"success": True, "accounts": []})

    db = get_db()
    # 支持搜索邮箱、备注和标签
    cursor = db.execute(
        """
        SELECT DISTINCT a.*, g.name as group_name, g.color as group_color
        FROM accounts a
        LEFT JOIN groups g ON a.group_id = g.id
        LEFT JOIN account_tags at ON a.id = at.account_id
        LEFT JOIN tags t ON at.tag_id = t.id
        WHERE a.email LIKE ? OR a.remark LIKE ? OR t.name LIKE ?
        ORDER BY a.created_at DESC
    """,
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    )

    rows = cursor.fetchall()

    # 批量加载标签与最后刷新状态，避免 N+1 查询
    account_rows: List[Dict[str, Any]] = [dict(r) for r in rows]
    try:
        account_ids = [int(a.get("id")) for a in account_rows if a.get("id") is not None]
    except Exception:
        account_ids = []

    tags_by_account: Dict[int, List[Dict[str, Any]]] = {}
    last_log_by_account: Dict[int, Dict[str, Any]] = {}
    if account_ids:
        try:
            placeholders = ",".join(["?"] * len(account_ids))
            tag_rows = db.execute(
                f"""
                SELECT at.account_id as account_id, t.*
                FROM account_tags at
                JOIN tags t ON t.id = at.tag_id
                WHERE at.account_id IN ({placeholders})
                ORDER BY at.account_id ASC, t.created_at DESC
            """,
                account_ids,
            ).fetchall()
            for tr in tag_rows:
                tag_dict = dict(tr)
                acc_id = tag_dict.pop("account_id", None)
                if acc_id is None:
                    continue
                tags_by_account.setdefault(int(acc_id), []).append(tag_dict)
        except Exception:
            tags_by_account = {}

        try:
            placeholders = ",".join(["?"] * len(account_ids))
            log_rows = db.execute(
                f"""
                SELECT l.account_id, l.status, l.error_message, l.created_at
                FROM account_refresh_logs l
                JOIN (
                    SELECT account_id, MAX(id) as max_id
                    FROM account_refresh_logs
                    WHERE account_id IN ({placeholders})
                    GROUP BY account_id
                ) latest
                ON l.account_id = latest.account_id AND l.id = latest.max_id
            """,
                account_ids,
            ).fetchall()
            for lr in log_rows:
                try:
                    last_log_by_account[int(lr["account_id"])] = dict(lr)
                except Exception:
                    continue
        except Exception:
            last_log_by_account = {}

    safe_accounts = []
    for acc in account_rows:
        acc_id = acc.get("id")
        try:
            acc_id_int = int(acc_id)
        except Exception:
            acc_id_int = None

        tags = tags_by_account.get(acc_id_int, []) if acc_id_int is not None else []
        last_refresh_log = last_log_by_account.get(acc_id_int) if acc_id_int is not None else None

        safe_accounts.append(
            {
                "id": acc["id"],
                "email": acc["email"],
                "account_type": acc.get("account_type") or "outlook",
                "provider": acc.get("provider") or "outlook",
                "client_id": (acc["client_id"][:8] + "..." if len(acc["client_id"]) > 8 else acc["client_id"]),
                "group_id": acc["group_id"],
                "group_name": acc["group_name"] if acc["group_name"] else "默认分组",
                "group_color": acc["group_color"] if acc["group_color"] else "#666666",
                "remark": acc["remark"] if acc["remark"] else "",
                "status": acc["status"] if acc["status"] else "active",
                "created_at": acc["created_at"] if acc["created_at"] else "",
                "updated_at": acc["updated_at"] if acc["updated_at"] else "",
                "tags": tags,
                "telegram_push_enabled": bool(acc.get("telegram_push_enabled")),
                "notification_enabled": bool(acc.get("telegram_push_enabled")),
                "last_refresh_status": (last_refresh_log.get("status") if last_refresh_log else None),
                "last_refresh_error": (last_refresh_log.get("error_message") if last_refresh_log else None),
                "latest_email_subject": acc.get("latest_email_subject", ""),
                "latest_email_from": acc.get("latest_email_from", ""),
                "latest_email_folder": acc.get("latest_email_folder", ""),
                "latest_email_received_at": acc.get("latest_email_received_at", ""),
                "latest_verification_code": acc.get("latest_verification_code", ""),
                "latest_verification_folder": acc.get("latest_verification_folder", ""),
                "latest_verification_received_at": acc.get("latest_verification_received_at", ""),
            }
        )

    return jsonify({"success": True, "accounts": safe_accounts})


# ==================== 导出功能 API ====================
