"""First-run / default-path guide for self-hosted installs.

Secret-free projection for dashboard: Cloudflare built-in, plugins, API key, smoke.
"""

from __future__ import annotations

from typing import Any


def _step(
    *,
    key: str,
    title: str,
    detail: str,
    done: bool,
    action: str,
    optional: bool = False,
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "detail": detail,
        "done": bool(done),
        "action": action,
        "optional": bool(optional),
    }


def build_setup_first_run_guide() -> dict[str, Any]:
    from mailops.repositories import accounts as accounts_repo
    from mailops.repositories import settings as settings_repo
    from mailops.services.provider_catalog.catalog import temp_mail_provider_config_status
    from mailops.services.temp_mail_plugin_manager import get_installed_plugins

    try:
        api_key_set = bool(settings_repo.get_external_api_key())
    except Exception:
        api_key_set = False

    try:
        cf_status = temp_mail_provider_config_status("cloudflare_temp_mail")
        cf_ready = bool(cf_status.get("configured"))
        cf_missing = list(cf_status.get("missing_config") or [])
    except Exception:
        cf_ready = False
        cf_missing = ["cf_worker_base_url"]

    try:
        installed_plugins = get_installed_plugins()
        plugin_count = len(installed_plugins) if isinstance(installed_plugins, list) else 0
    except Exception:
        plugin_count = 0

    account_total = 0
    try:
        if hasattr(accounts_repo, "count_accounts"):
            account_total = int(accounts_repo.count_accounts() or 0)
        else:
            from mailops.db import get_db

            row = get_db().execute("SELECT COUNT(*) AS c FROM accounts").fetchone()
            account_total = int((row["c"] if row else 0) or 0)
    except Exception:
        try:
            from mailops.db import get_db

            row = get_db().execute("SELECT COUNT(*) AS c FROM accounts").fetchone()
            account_total = int((row["c"] if row else 0) or 0)
        except Exception:
            account_total = 0

    steps = [
        _step(
            key="cloudflare",
            title="配置 Cloudflare 临时邮箱",
            detail=(
                "内置唯一默认源。填写 Worker 地址与 Admin Key。"
                if not cf_ready
                else "Cloudflare Temp Mail 已就绪。"
            )
            + (f" 缺失：{', '.join(cf_missing)}" if cf_missing and not cf_ready else ""),
            done=cf_ready,
            action="settings:temp-mail:cloudflare",
        ),
        _step(
            key="plugins",
            title="按需安装插件",
            detail=(
                f"已安装 {plugin_count} 个插件。需要 GPTMail / Mail.tm 等时在插件管理安装。"
                if plugin_count
                else "内置仅 Cloudflare。GPTMail / Mail.tm / DuckMail 等从插件管理一键安装。"
            ),
            done=plugin_count > 0,
            action="settings:temp-mail:plugins",
            optional=True,
        ),
        _step(
            key="api_key",
            title="生成对外 API Key",
            detail="给其它程序调用 /api/v1/external/* 使用。生成后请保存设置。",
            done=api_key_set,
            action="settings:api-security:generate-key",
        ),
        _step(
            key="smoke",
            title="复制 Smoke 自检命令",
            detail="用 smoke 脚本验证 health / providers / integration-bundle 是否通。",
            done=api_key_set,
            action="copy:smoke",
        ),
        _step(
            key="accounts",
            title="导入 Outlook / IMAP 账号",
            detail="批量号用于读信与号池 claim；可稍后在邮箱页导入。",
            done=account_total > 0,
            action="mailbox:import",
            optional=True,
        ),
    ]

    required_pending = [s for s in steps if not s["optional"] and not s["done"]]
    show = bool(required_pending) or (account_total == 0 and not cf_ready)

    return {
        "version": 1,
        "show": show,
        "title": "新装快速路径",
        "subtitle": "Cloudflare 内置 · 插件扩展 · API Key · Smoke 自检",
        "steps": steps,
        "summary": {
            "cloudflare_ready": cf_ready,
            "plugin_count": plugin_count,
            "api_key_set": api_key_set,
            "account_total": account_total,
            "required_pending": len(required_pending),
        },
        "examples": get_external_api_three_examples(),
    }


def get_external_api_three_examples(*, base_url: str = "http://127.0.0.1:5000") -> list[dict[str, str]]:
    """Fixed 3-example external API quickstart (secret-free placeholders)."""
    root = str(base_url or "http://127.0.0.1:5000").rstrip("/")
    return [
        {
            "key": "temp_claim",
            "title": "1. 领临时邮箱",
            "detail": "创建任务临时邮箱会话（可指定 provider 或 task_temp_only）",
            "method": "POST",
            "path": "/api/v1/external/mailbox-sessions/start",
            "snippet": (
                f"curl -s -X POST '{root}/api/v1/external/mailbox-sessions/start' \\\n"
                "  -H 'X-API-Key: <your-api-key>' \\\n"
                "  -H 'Content-Type: application/json' \\\n"
                "  -d '{\"caller_id\":\"demo\",\"task_id\":\"job-1\",\"task_temp_only\":true}'"
            ),
        },
        {
            "key": "verification_code",
            "title": "2. 读验证码",
            "detail": "对已 start 的会话读取 verification_code",
            "method": "POST",
            "path": "/api/v1/external/mailbox-sessions/read",
            "snippet": (
                f"curl -s -X POST '{root}/api/v1/external/mailbox-sessions/read' \\\n"
                "  -H 'X-API-Key: <your-api-key>' \\\n"
                "  -H 'Content-Type: application/json' \\\n"
                "  -d '{\"session_token\":\"<session_token>\",\"read_action\":\"verification_code\"}'"
            ),
        },
        {
            "key": "pool_claim",
            "title": "3. Claim Outlook 号池",
            "detail": "从邮箱池随机领取长期号（需开启 pool 与 Key 权限）",
            "method": "POST",
            "path": "/api/v1/external/pool/claim-random",
            "snippet": (
                f"curl -s -X POST '{root}/api/v1/external/pool/claim-random' \\\n"
                "  -H 'X-API-Key: <your-api-key>' \\\n"
                "  -H 'Content-Type: application/json' \\\n"
                "  -d '{\"caller_id\":\"demo\",\"task_id\":\"job-1\",\"project_key\":\"app-a\"}'"
            ),
        },
    ]


def build_ops_health_snapshot(
    *,
    account_status: dict[str, Any] | None,
    refresh_health: dict[str, Any] | None,
    command_center: dict[str, Any] | None,
    external_api_stats: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compose a compact ops health strip from existing overview payloads."""
    accounts = account_status if isinstance(account_status, dict) else {}
    refresh = refresh_health if isinstance(refresh_health, dict) else {}
    center = command_center if isinstance(command_center, dict) else {}
    provider = center.get("provider_readiness") if isinstance(center.get("provider_readiness"), dict) else {}
    api_stats = external_api_stats if isinstance(external_api_stats, dict) else {}
    api_kpi = api_stats.get("kpi") if isinstance(api_stats.get("kpi"), dict) else {}
    api_health = api_stats.get("health") if isinstance(api_stats.get("health"), dict) else {}

    token_fail = int(refresh.get("last_fail_count") or 0)
    token_expired = int(accounts.get("expired") or 0)
    token_error = int(accounts.get("error") or 0)
    provider_needs = int(provider.get("needs_config") or 0)
    provider_ready = int(provider.get("ready") or 0)
    today_calls = int(api_kpi.get("today_calls") or 0)
    # Prefer week error_count as available; today errors approximated via health if present
    week_errors = int(api_kpi.get("error_count") or 0)
    api_status = str(api_health.get("status") or ("idle" if today_calls == 0 else "ok")).strip().lower()

    return {
        "token": {
            "last_fail_count": token_fail,
            "expired_accounts": token_expired,
            "error_accounts": token_error,
            "success_rate_7d": refresh.get("success_rate_7d"),
            "last_run_at": refresh.get("last_run_at") or "",
            "status": "bad" if token_fail > 0 or token_error > 0 else ("warn" if token_expired > 0 else "ok"),
        },
        "temp_provider": {
            "needs_config": provider_needs,
            "ready": provider_ready,
            "active": int(provider.get("active") or 0),
            "status": "bad" if provider_needs > 0 else ("ok" if provider_ready > 0 else "warn"),
        },
        "external_api": {
            "today_calls": today_calls,
            "week_errors": week_errors,
            "status": api_status or "unknown",
            "top_error_endpoint": str(api_health.get("top_error_endpoint") or ""),
        },
    }
