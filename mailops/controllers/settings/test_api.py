from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from flask import jsonify, request

from mailops import config
from mailops.audit import log_audit
from mailops.db import get_db
from mailops.errors import build_error_payload
from mailops.repositories import external_api_keys as external_api_keys_repo
from mailops.repositories import settings as settings_repo
from mailops.security.auth import login_required
from mailops.security.crypto import (
    decrypt_data,
    encrypt_data,
    hash_password,
    is_encrypted,
)
from mailops.services import webhook_push
from mailops.services.external_api_contract_check import get_external_api_contract_check
from mailops.services.provider_catalog import get_mailbox_provider_catalog, temp_mail_provider_label
from mailops.services.verification_extractor import probe_verification_ai_runtime

from .helpers import _json_error

# ==================== 设置 API ====================


@login_required
def api_validate_cron() -> Any:
    """验证 Cron 表达式"""
    try:
        from croniter import croniter
    except ImportError:
        return _json_error(
            "CRONITER_NOT_INSTALLED",
            "croniter 库未安装，请运行: pip install croniter",
            status=500,
            message_en="croniter is not installed. Please run: pip install croniter",
        )

    data = request.json
    cron_expr = data.get("cron_expression", "").strip()

    if not cron_expr:
        return _json_error(
            "CRON_EXPRESSION_REQUIRED",
            "Cron 表达式不能为空",
            status=400,
            message_en="Cron expression is required",
            extra={"valid": False},
        )

    try:
        base_time = datetime.now()
        cron = croniter(cron_expr, base_time)

        next_run = cron.get_next(datetime)

        future_runs = []
        temp_cron = croniter(cron_expr, base_time)
        for _ in range(5):
            future_runs.append(temp_cron.get_next(datetime).isoformat())

        return jsonify(
            {
                "success": True,
                "valid": True,
                "next_run": next_run.isoformat(),
                "future_runs": future_runs,
            }
        )
    except Exception as e:
        return _json_error(
            "CRON_EXPRESSION_INVALID",
            "Cron 表达式无效",
            status=400,
            message_en="Invalid cron expression",
            details=str(e),
            extra={"valid": False},
        )


@login_required
def api_test_email() -> Any:
    """发送邮件通知测试消息。按“先保存，再测试”规则，仅使用已保存的接收邮箱。"""
    from mailops.services import email_push

    try:
        recipient = email_push.send_test_email()
    except email_push.EmailPushError as exc:
        return _json_error(
            exc.code,
            exc.message,
            status=exc.status,
            message_en=exc.message_en,
            details=exc.details,
        )

    log_audit("email_notification_test", "settings", None, f"recipient={recipient}")
    return jsonify(
        {
            "success": True,
            "message": "测试邮件已提交，请检查收件箱",
            "message_en": "Test email accepted. Please check your inbox",
            "recipient": recipient,
        }
    )


@login_required
def api_test_webhook() -> Any:
    """发送 Webhook 测试消息。按“先保存，再测试”规则，仅使用已保存配置。"""
    try:
        result = webhook_push.send_test_webhook_message()
    except webhook_push.WebhookPushError as exc:
        details_text = str(exc.details or "").strip()
        log_audit(
            "webhook_notification_test",
            "settings",
            None,
            f"success=false code={exc.code} details={details_text[:200]}",
        )
        return _json_error(
            exc.code,
            exc.message,
            status=exc.status,
            message_en=exc.message_en,
            details=exc.details,
        )

    safe_url = str(result.get("url") or "")
    log_audit("webhook_notification_test", "settings", None, f"success=true url={safe_url}")
    return jsonify(
        {
            "success": True,
            "message": "Webhook 测试消息已发送",
            "message_en": "Webhook test message sent",
            "url": safe_url,
        }
    )


@login_required
def api_test_verification_ai() -> Any:
    """测试已保存的系统级验证码 AI 配置可用性（连通性优先）。"""
    data = request.get_json(silent=True) or {}

    ai_config = {
        "enabled": settings_repo.get_verification_ai_enabled(),
        "base_url": settings_repo.get_verification_ai_base_url(),
        "api_key": settings_repo.get_verification_ai_api_key(),
        "model": settings_repo.get_verification_ai_model(),
    }

    sample_email = {
        "subject": str(data.get("subject") or "Verification test").strip(),
        "body": str(data.get("body") or "Your verification code is 123456").strip(),
        "body_html": str(data.get("body_html") or "").strip(),
    }
    if not sample_email["body_html"]:
        sample_email["body_html"] = f"<p>{sample_email['body']}</p>"

    code_length = str(data.get("code_length") or "6-6").strip()
    code_regex_raw = data.get("code_regex")
    code_regex = str(code_regex_raw).strip() if code_regex_raw is not None and str(code_regex_raw).strip() else None

    probe = probe_verification_ai_runtime(
        ai_config=ai_config,
        sample_email=sample_email,
        code_regex=code_regex,
        code_length=code_length,
        code_source="all",
    )

    contract_ok = bool(probe.get("ok"))
    http_status = probe.get("http_status")
    connectivity_ok = isinstance(http_status, int) and 200 <= http_status < 300

    # 连通性探测口径：只要请求拿到 2xx，即视为“可连通”。
    # 契约校验结果仍保留在 contract_ok / probe.error 中，供排障参考。
    final_ok = connectivity_ok or contract_ok

    log_audit(
        "verification_ai_test",
        "settings",
        None,
        (f"ok={final_ok} connectivity_ok={connectivity_ok} " f"contract_ok={contract_ok} error={probe.get('error') or ''}"),
    )

    return jsonify(
        {
            "success": True,
            "ok": final_ok,
            "connectivity_ok": connectivity_ok,
            "contract_ok": contract_ok,
            "enabled": ai_config.get("enabled", False),
            "probe": probe,
        }
    )


@login_required
def api_sync_cf_worker_domains() -> Any:
    """
    从 CF Worker 的 /open_api/settings 接口同步域名列表到本地配置。

    成功后自动写入：
    - cf_worker_domains：CF Worker 上配置的所有域名（v0.3: 独立 key，不覆盖兼容临时邮箱桥接配置）
    - cf_worker_default_domain：CF Worker 的默认域名（defaultDomains 第一个）

    返回：{"success": True, "domains": [...], "default_domain": "...", "message": "..."}
    """
    from mailops.services.temp_mail_provider_cf import CloudflareTempMailProvider
    from mailops.services.temp_mail_provider_factory import (
        TempMailProviderFactoryError,
    )

    cf_base_url = settings_repo.get_cf_worker_base_url()
    if not cf_base_url:
        return _json_error(
            "CF_WORKER_NOT_CONFIGURED",
            "请先配置 CF Worker 地址（cf_worker_base_url）",
            status=400,
        )

    try:
        provider = CloudflareTempMailProvider()
        result = provider.get_cf_worker_domains()
    except Exception as exc:
        return _json_error(
            "CF_WORKER_SYNC_FAILED",
            f"CF Worker 域名同步失败: {exc}",
            status=502,
        )

    if not result.get("success"):
        return _json_error(
            result.get("error_code") or "CF_WORKER_SYNC_FAILED",
            result.get("error") or "CF Worker 域名同步失败",
            status=502,
        )

    domains: list[str] = result.get("domains") or []
    default_domain: str = result.get("default_domain") or ""

    if not domains:
        return _json_error(
            "CF_WORKER_NO_DOMAINS",
            "CF Worker 未返回任何域名，请检查 CF Worker 配置",
            status=502,
        )

    # 构建 cf_worker_domains 格式（带 enabled/is_default 标记）
    # v0.3: 同步到独立的 cf_worker_* key，不覆盖兼容临时邮箱桥接的 temp_mail_* key
    domains_payload = [
        {
            "name": d,
            "enabled": True,
        }
        for d in domains
    ]
    db = get_db()
    try:
        db.execute("BEGIN")
        settings_repo.set_setting(
            "cf_worker_domains",
            __import__("json").dumps(domains_payload, ensure_ascii=False),
            commit=False,
        )
        if default_domain:
            settings_repo.set_setting("cf_worker_default_domain", default_domain, commit=False)
        db.commit()
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        return _json_error(
            "INTERNAL_ERROR",
            f"域名同步写入失败: {exc}",
            status=500,
        )

    log_audit(
        "sync",
        "settings",
        None,
        f"cf_worker_domains_synced domains={','.join(domains)} default={default_domain}",
    )
    return jsonify(
        {
            "success": True,
            "domains": domains,
            "default_domain": default_domain,
            "title": result.get("title") or "",
            "version": result.get("version") or "",
            "message": f"已同步 {len(domains)} 个域名，默认域名：{default_domain or '（未指定）'}",
        }
    )


@login_required
def api_test_telegram() -> Any:
    """发送 Telegram 测试消息，验证 bot_token + chat_id 配置是否正确"""
    from mailops.services.telegram_push import _send_telegram_message

    bot_token_raw = settings_repo.get_setting("telegram_bot_token", "")
    chat_id = settings_repo.get_setting("telegram_chat_id", "")

    if not bot_token_raw or not chat_id:
        return _json_error(
            "TELEGRAM_NOT_CONFIGURED",
            "请先配置 Telegram Bot Token 和 Chat ID",
            message_en="Please configure Telegram Bot Token and Chat ID first",
        )

    bot_token = decrypt_data(bot_token_raw) if is_encrypted(bot_token_raw) else bot_token_raw

    ok = _send_telegram_message(bot_token, chat_id, "✅ Outlook Email Plus 测试消息：配置正确！")
    if ok:
        log_audit("telegram_test", "settings", None, "测试消息发送成功")
        return jsonify(
            {
                "success": True,
                "message": "测试消息已发送，请检查 Telegram",
                "message_en": "Test message sent successfully. Please check Telegram",
            }
        )
    return _json_error(
        "TELEGRAM_TEST_SEND_FAILED",
        "发送失败，请检查 Bot Token 和 Chat ID 是否正确",
        message_en="Failed to send test message. Please check whether the Bot Token and Chat ID are correct",
    )


@login_required
def api_test_telegram_proxy() -> Any:
    """测试 Telegram 代理连通性：用指定代理实际请求 api.telegram.org/getMe"""
    import time

    import requests as req

    from mailops.services.graph import build_proxies

    data = request.get_json(silent=True) or {}
    proxy_url = str(data.get("proxy_url", "")).strip()

    bot_token = settings_repo.get_telegram_bot_token()
    if not bot_token:
        return _json_error(
            "TELEGRAM_NOT_CONFIGURED",
            "请先配置 Telegram Bot Token",
            message_en="Please configure Telegram Bot Token first",
        )

    proxies = build_proxies(proxy_url) if proxy_url else None
    test_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    t0 = time.monotonic()
    try:
        resp = req.get(test_url, proxies=proxies, timeout=10)
        latency_ms = int((time.monotonic() - t0) * 1000)
        if resp.ok:
            return jsonify(
                {
                    "success": True,
                    "ok": True,
                    "message": "代理连通成功",
                    "latency_ms": latency_ms,
                }
            )
        return jsonify(
            {
                "success": True,
                "ok": False,
                "message": f"代理可达但 Telegram 返回错误 HTTP {resp.status_code}",
                "latency_ms": latency_ms,
            }
        )
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return jsonify(
            {
                "success": True,
                "ok": False,
                "message": f"连接失败：{exc}",
                "latency_ms": latency_ms,
            }
        )
