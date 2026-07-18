from __future__ import annotations

import time
from typing import Any

from flask import jsonify

from mailops.repositories import overview as overview_repo
from mailops.security.auth import login_required
from mailops.services.overview_command_center import get_overview_command_center, get_overview_command_center_degraded

# ==================== 概览 summary 进程级 TTL 缓存 ====================
# summary 是 dashboard 首屏加载的聚合查询（6 条 SQL），
# 在单 sync worker 下频繁刷新会加重排队。30 秒 TTL 兼顾数据实时性与请求降频。
_OVERVIEW_SUMMARY_CACHE: dict | None = None
_OVERVIEW_SUMMARY_CACHE_AT: float = 0.0
_OVERVIEW_SUMMARY_CACHE_TTL: int = 30  # 秒


@login_required
def api_get_overview_summary() -> Any:
    global _OVERVIEW_SUMMARY_CACHE, _OVERVIEW_SUMMARY_CACHE_AT
    now = time.time()
    if _OVERVIEW_SUMMARY_CACHE is not None and (now - _OVERVIEW_SUMMARY_CACHE_AT) < _OVERVIEW_SUMMARY_CACHE_TTL:
        return jsonify(_OVERVIEW_SUMMARY_CACHE)
    result = overview_repo.get_overview_summary()
    try:
        result["command_center"] = get_overview_command_center()
    except Exception:
        result["command_center"] = get_overview_command_center_degraded()

    try:
        from mailops.services.setup_first_run import build_ops_health_snapshot, build_setup_first_run_guide

        result["setup_guide"] = build_setup_first_run_guide()
    except Exception:
        result["setup_guide"] = {"version": 1, "show": False, "steps": [], "examples": []}

    try:
        from mailops.services.setup_first_run import build_ops_health_snapshot

        api_stats = overview_repo.get_external_api_stats()
        result["ops_health"] = build_ops_health_snapshot(
            account_status=result.get("account_status"),
            refresh_health=result.get("refresh_health"),
            command_center=result.get("command_center"),
            external_api_stats=api_stats,
        )
        # Lightweight KPI for summary strip (avoid full external-api tab payload on summary).
        kpi = api_stats.get("kpi") if isinstance(api_stats.get("kpi"), dict) else {}
        result["external_api_today"] = {
            "today_calls": int(kpi.get("today_calls") or 0),
            "error_count": int(kpi.get("error_count") or 0),
            "success_rate": kpi.get("success_rate"),
        }
    except Exception:
        result["ops_health"] = {}
        result["external_api_today"] = {"today_calls": 0, "error_count": 0}

    _OVERVIEW_SUMMARY_CACHE = result
    _OVERVIEW_SUMMARY_CACHE_AT = now
    return jsonify(result)


@login_required
def api_get_overview_verification() -> Any:
    return jsonify(overview_repo.get_verification_stats())


@login_required
def api_get_overview_external_api() -> Any:
    return jsonify(overview_repo.get_external_api_stats())


@login_required
def api_get_overview_pool() -> Any:
    return jsonify(overview_repo.get_pool_stats())


@login_required
def api_get_overview_activity() -> Any:
    return jsonify(overview_repo.get_activity_stats())
