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

from .constants import _HEALTHZ_BOOT_ID
from .helpers import _safe_demo_workspace_metadata, utcnow

@login_required
def api_bootstrap() -> Any:
    """首屏引导接口：仅返回首页初始化必需的最少字段，避免走完整 /api/settings 的重查询链路。

    当前 /api/settings 会执行：解密 Telegram token、解密 Watchtower token、
    查询所有 external_api_keys + usage_summary、解密 verification_ai_api_key 等，
    对于首页只需要布局状态和轮询配置的场景来说过于重。

    本接口只查 6 个 key，不做解密，不做聚合统计。
    """
    ui_layout_raw = settings_repo.get_setting("ui_layout_v2", "")
    ui_layout = None
    if ui_layout_raw:
        try:
            import json as _json

            parsed = _json.loads(ui_layout_raw)
            if isinstance(parsed, dict) and parsed.get("version") == 2:
                ui_layout = parsed
        except Exception:
            pass
    if not ui_layout:
        ui_layout = {
            "version": 2,
            "sidebar": {"collapsed": False},
            "mailbox": {"groupPanelWidth": 220, "accountPanelWidth": 280},
            "tempEmails": {"listPanelWidth": 300},
        }

    return jsonify(
        {
            "success": True,
            "bootstrap": {
                "ui_layout_v2": ui_layout,
                "enable_auto_polling": settings_repo.get_setting("enable_auto_polling", "false") == "true",
                "polling_interval": int(settings_repo.get_setting("polling_interval", "10")),
                "polling_count": int(settings_repo.get_setting("polling_count", "5")),
                "enable_compact_auto_poll": settings_repo.get_setting("enable_compact_auto_poll", "false") == "true",
                "compact_poll_interval": int(settings_repo.get_setting("compact_poll_interval", "10")),
                "compact_poll_max_count": int(settings_repo.get_setting("compact_poll_max_count", "5")),
                "demo_workspace": _safe_demo_workspace_metadata(),
            },
        }
    )

@login_required
def api_reload_plugins() -> Any:
    from outlook_web.services.temp_mail_provider_factory import reload_plugins

    return jsonify(
        {
            "success": True,
            "code": "OK",
            "message": "插件刷新完成",
            "data": reload_plugins(),
        }
    )


# ==================== 系统 API ====================

def healthz() -> Any:
    """基础健康检查（用于容器/反代探活）"""
    return (
        jsonify(
            {
                "status": "ok",
                "version": APP_VERSION,
                "boot_id": _HEALTHZ_BOOT_ID,
            }
        ),
        200,
    )

@login_required
def api_system_health() -> Any:
    """管理员健康检查：可服务/可刷新状态概览"""
    conn = create_sqlite_connection()
    try:
        # DB 可用性
        db_ok = True
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception:
            db_ok = False

        # Scheduler 心跳
        heartbeat_row = conn.execute("""
            SELECT updated_at
            FROM settings
            WHERE key = 'scheduler_heartbeat'
        """).fetchone()

        heartbeat_age_seconds = None
        if heartbeat_row and heartbeat_row["updated_at"]:
            try:
                hb_time = datetime.fromisoformat(heartbeat_row["updated_at"])
                heartbeat_age_seconds = int((utcnow() - hb_time).total_seconds())
            except Exception:
                heartbeat_age_seconds = None

        scheduler_enabled = settings_repo.get_setting("enable_scheduled_refresh", "true").lower() == "true"
        scheduler_autostart = config.get_scheduler_autostart_default()
        scheduler_healthy = (heartbeat_age_seconds is not None) and (heartbeat_age_seconds <= 120)

        # 刷新锁/运行中
        lock_row = conn.execute(
            """
            SELECT owner_id, expires_at
            FROM distributed_locks
            WHERE name = ?
        """,
            (REFRESH_LOCK_NAME,),
        ).fetchone()
        locked = bool(lock_row and lock_row["expires_at"] and lock_row["expires_at"] > time.time())

        running_run = conn.execute("""
            SELECT id, trigger_source, started_at, trace_id
            FROM refresh_runs
            WHERE status = 'running'
            ORDER BY started_at DESC
            LIMIT 1
        """).fetchone()

        return jsonify(
            {
                "success": True,
                "health": {
                    "service": "ok",
                    "database": "ok" if db_ok else "error",
                    "scheduler": {
                        "enabled": scheduler_enabled,
                        "autostart": scheduler_autostart,
                        "heartbeat_age_seconds": heartbeat_age_seconds,
                        "healthy": scheduler_healthy if scheduler_enabled else True,
                    },
                    "refresh": {
                        "locked": locked,
                        "running": dict(running_run) if running_run else None,
                    },
                    "server_time_utc": utcnow().isoformat() + "Z",
                },
            }
        )
    finally:
        conn.close()

@login_required
def api_system_diagnostics() -> Any:
    """管理员诊断信息：关键状态一致性/过期清理可见性"""
    conn = create_sqlite_connection()
    try:
        now_ts = time.time()

        export_tokens_count = conn.execute(
            """
            SELECT COUNT(*) as c
            FROM export_verify_tokens
            WHERE expires_at > ?
        """,
            (now_ts,),
        ).fetchone()["c"]

        locked_ip_count = conn.execute(
            """
            SELECT COUNT(*) as c
            FROM login_attempts
            WHERE locked_until_at IS NOT NULL AND locked_until_at > ?
        """,
            (now_ts,),
        ).fetchone()["c"]

        running_runs = conn.execute("""
            SELECT id, trigger_source, started_at, trace_id
            FROM refresh_runs
            WHERE status = 'running'
            ORDER BY started_at DESC
            LIMIT 5
        """).fetchall()

        last_runs = conn.execute("""
            SELECT id, trigger_source, status, started_at, finished_at, total, success_count, failed_count, trace_id
            FROM refresh_runs
            ORDER BY started_at DESC
            LIMIT 10
        """).fetchall()

        locks = conn.execute("""
            SELECT name, owner_id, acquired_at, expires_at
            FROM distributed_locks
            ORDER BY name ASC
        """).fetchall()

        # 数据库升级状态（可验证）
        schema_version_row = conn.execute(
            "SELECT value, updated_at FROM settings WHERE key = ?",
            (DB_SCHEMA_VERSION_KEY,),
        ).fetchone()
        schema_version = int(schema_version_row["value"]) if schema_version_row else 0

        last_migration = None
        try:
            mig = conn.execute("""
                SELECT id, from_version, to_version, status, started_at, finished_at, error, trace_id
                FROM schema_migrations
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            last_migration = dict(mig) if mig else None
        except Exception:
            last_migration = None

        return jsonify(
            {
                "success": True,
                "diagnostics": {
                    "export_verify_tokens_active": export_tokens_count,
                    "login_locked_ip_count": locked_ip_count,
                    "running_runs": [dict(r) for r in running_runs],
                    "last_runs": [dict(r) for r in last_runs],
                    "locks": [dict(r) for r in locks],
                    "schema": {
                        "version": schema_version,
                        "target_version": DB_SCHEMA_VERSION,
                        "up_to_date": schema_version >= DB_SCHEMA_VERSION,
                        "last_migration": last_migration,
                    },
                },
            }
        )
    finally:
        conn.close()

@login_required
def api_system_upgrade_status() -> Any:
    """数据库升级状态（用于验收"升级过程可验证/失败可定位"）"""
    from outlook_web import config as app_config

    conn = create_sqlite_connection()
    try:
        row = conn.execute(
            "SELECT value, updated_at FROM settings WHERE key = ?",
            (DB_SCHEMA_VERSION_KEY,),
        ).fetchone()
        schema_version = int(row["value"]) if row and row["value"] is not None else 0

        last_trace_row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY,),
        ).fetchone()
        last_error_row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (DB_SCHEMA_LAST_UPGRADE_ERROR_KEY,),
        ).fetchone()

        last_migration = None
        try:
            mig = conn.execute("""
                SELECT id, from_version, to_version, status, started_at, finished_at, error, trace_id
                FROM schema_migrations
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            last_migration = dict(mig) if mig else None
        except Exception:
            last_migration = None

        database_path = app_config.get_database_path()
        backup_hint = {
            "database_path": database_path,
            "linux_example": f'cp "{database_path}" "{database_path}.backup"',
            "windows_example": f'copy "{database_path}" "{database_path}.backup"',
        }

        return jsonify(
            {
                "success": True,
                "upgrade": {
                    "schema_version": schema_version,
                    "target_version": DB_SCHEMA_VERSION,
                    "up_to_date": schema_version >= DB_SCHEMA_VERSION,
                    "last_upgrade_trace_id": (last_trace_row["value"] if last_trace_row else ""),
                    "last_upgrade_error": (last_error_row["value"] if last_error_row else ""),
                    "last_migration": last_migration,
                    "backup_hint": backup_hint,
                },
            }
        )
    finally:
        conn.close()


# ==================== External System API ====================

@api_key_required
@external_api_guards()
def api_external_health() -> Any:
    """对外健康检查（不依赖登录态）"""
    conn = create_sqlite_connection()
    try:
        db_ok = True
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception:
            db_ok = False

        probe_summary: dict[str, Any] = {
            "upstream_probe_ok": None,
            "last_probe_at": "",
            "last_probe_error": "",
        }
        if db_ok:
            try:
                probe_summary = external_api_service.probe_instance_upstream(cache_ttl_seconds=60)
            except Exception:
                probe_summary = {
                    "upstream_probe_ok": False,
                    "last_probe_at": utcnow().isoformat() + "Z",
                    "last_probe_error": "实例上游探测执行失败",
                }

        data = {
            "status": "ok",
            "service": "outlook-email-plus",
            "version": APP_VERSION,
            "server_time_utc": utcnow().isoformat() + "Z",
            "database": "ok" if db_ok else "error",
            "upstream_probe_ok": probe_summary.get("upstream_probe_ok"),
            "last_probe_at": probe_summary.get("last_probe_at") or "",
            "last_probe_error": probe_summary.get("last_probe_error") or "",
        }
        consumer = get_external_api_consumer() or {}
        data["readiness"] = get_external_api_readiness_summary(
            consumer=consumer,
            database_ok=db_ok,
            upstream_probe_ok=data["upstream_probe_ok"],
        )
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr="",
            endpoint="/api/v1/external/health",
            status="ok",
            details={
                "database": data["database"],
                "upstream_probe_ok": data["upstream_probe_ok"],
                "readiness_status": data["readiness"].get("status"),
                "pool_status": data["readiness"].get("pool", {}).get("status"),
            },
        )
        return jsonify(external_api_service.ok(data))
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr="",
            endpoint="/api/v1/external/health",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500
    finally:
        conn.close()


# ==================== 版本更新检测 ====================
