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

from .helpers import _coerce_int_range, _json_error, _mask_secret_value, _plugin_settings_contract

# ==================== 设置 API ====================


@login_required
def api_get_settings() -> Any:
    """获取所有设置"""
    all_settings = settings_repo.get_all_settings()

    # 仅返回前端需要的设置项（避免把敏感字段/内部状态直接返回）
    safe_settings = {
        "refresh_interval_days": all_settings.get("refresh_interval_days", "30"),
        "refresh_delay_seconds": all_settings.get("refresh_delay_seconds", "5"),
        "refresh_cron": all_settings.get("refresh_cron", "0 2 * * *"),
        "use_cron_schedule": all_settings.get("use_cron_schedule", "false"),
        "enable_scheduled_refresh": all_settings.get("enable_scheduled_refresh", "true"),
        # 轮询配置
        "enable_auto_polling": all_settings.get("enable_auto_polling", "false") == "true",
        "polling_interval": int(all_settings.get("polling_interval", "10")),
        "polling_count": int(all_settings.get("polling_count", "5")),
        # [Phase 3 deprecated] 简洁模式自动轮询配置 — 保留读取，向后兼容
        "enable_compact_auto_poll": all_settings.get("enable_compact_auto_poll", "false") == "true",
        "compact_poll_interval": int(all_settings.get("compact_poll_interval", "10")),
        "compact_poll_max_count": int(all_settings.get("compact_poll_max_count", "5")),
        "email_notification_enabled": all_settings.get("email_notification_enabled", "false").lower() == "true",
        "email_notification_recipient": all_settings.get("email_notification_recipient", ""),
        "webhook_notification_enabled": settings_repo.get_webhook_notification_enabled(),
        "webhook_notification_url": settings_repo.get_webhook_notification_url(),
        "webhook_notification_token": settings_repo.get_webhook_notification_token_masked(),
    }

    # 敏感字段：不返回明文/哈希，仅提供"是否已设置/脱敏展示"
    login_password_value = all_settings.get("login_password") or ""
    temp_mail_api_key_value = settings_repo.get_temp_mail_api_key()
    external_api_key_value = settings_repo.get_external_api_key()
    external_api_keys = external_api_keys_repo.list_external_api_keys(include_disabled=True)
    usage_summary = external_api_keys_repo.get_external_api_usage_summary(
        [item.get("consumer_key") or "" for item in external_api_keys]
    )
    for item in external_api_keys:
        item.update(
            usage_summary.get(
                item.get("consumer_key") or "",
                {
                    "today_total_count": 0,
                    "today_success_count": 0,
                    "today_error_count": 0,
                    "today_last_used_at": "",
                },
            )
        )
    safe_settings["login_password_set"] = bool(login_password_value)
    safe_settings["allow_login_password_change"] = config.get_allow_login_password_change()
    safe_settings["provider_config_file"] = config.get_provider_config_file_status()
    safe_settings["temp_mail_provider"] = settings_repo.get_temp_mail_provider(strict=False)
    safe_settings["temp_mail_provider_label"] = temp_mail_provider_label(safe_settings["temp_mail_provider"])
    safe_settings["temp_mail_api_base_url"] = settings_repo.get_temp_mail_api_base_url()
    safe_settings["temp_mail_api_key_set"] = bool(temp_mail_api_key_value)
    safe_settings["temp_mail_api_key_masked"] = _mask_secret_value(temp_mail_api_key_value) if temp_mail_api_key_value else ""
    safe_settings["temp_mail_domains"] = settings_repo.get_temp_mail_domains()
    safe_settings["temp_mail_default_domain"] = settings_repo.get_temp_mail_default_domain()
    safe_settings["temp_mail_prefix_rules"] = settings_repo.get_temp_mail_prefix_rules()
    # v0.3: CF Worker 独立域名配置（Tab 重构）
    safe_settings["cf_worker_domains"] = settings_repo.get_cf_worker_domains()
    safe_settings["cf_worker_default_domain"] = settings_repo.get_cf_worker_default_domain()
    safe_settings["cf_worker_prefix_rules"] = settings_repo.get_cf_worker_prefix_rules()
    # Cloudflare Worker 独立配置（与兼容临时邮箱桥接设置隔离）
    cf_admin_key_value = settings_repo.get_cf_worker_admin_key()
    emailnator_api_key_value = settings_repo.get_emailnator_api_key()
    duckmail_bearer_token_value = settings_repo.get_duckmail_bearer_token()
    tempmail_lol_api_key_value = settings_repo.get_tempmail_lol_api_key()
    safe_settings["cf_worker_base_url"] = settings_repo.get_cf_worker_base_url()
    safe_settings["cf_worker_admin_key_set"] = bool(cf_admin_key_value)
    safe_settings["cf_worker_admin_key_masked"] = _mask_secret_value(cf_admin_key_value) if cf_admin_key_value else ""
    safe_settings["emailnator_api_key_set"] = bool(emailnator_api_key_value)
    safe_settings["emailnator_api_key_masked"] = (
        _mask_secret_value(emailnator_api_key_value) if emailnator_api_key_value else ""
    )
    safe_settings["emailnator_email_types"] = settings_repo.get_emailnator_email_types()
    safe_settings["duckmail_api_base"] = settings_repo.get_duckmail_api_base()
    safe_settings["duckmail_bearer_token_set"] = bool(duckmail_bearer_token_value)
    safe_settings["duckmail_bearer_token_masked"] = (
        _mask_secret_value(duckmail_bearer_token_value) if duckmail_bearer_token_value else ""
    )
    safe_settings["tempmail_lol_api_key_set"] = bool(tempmail_lol_api_key_value)
    safe_settings["tempmail_lol_api_key_masked"] = (
        _mask_secret_value(tempmail_lol_api_key_value) if tempmail_lol_api_key_value else ""
    )
    for setting_key, field in _plugin_settings_contract().items():
        value = settings_repo.get_setting(setting_key, "")
        if field["secret"]:
            safe_settings[f"{setting_key}_set"] = bool(value)
            safe_settings[f"{setting_key}_masked"] = _mask_secret_value(value) if value else ""
        else:
            safe_settings[setting_key] = value
    safe_settings["external_api_key_set"] = bool(external_api_key_value)
    safe_settings["external_api_key_masked"] = _mask_secret_value(external_api_key_value) if external_api_key_value else ""
    safe_settings["external_api_keys"] = external_api_keys
    safe_settings["external_api_keys_count"] = len(external_api_keys)
    safe_settings["external_api_multi_key_set"] = bool(external_api_keys)

    # 验证码 AI 增强（系统级配置）
    verification_ai_api_key_value = settings_repo.get_verification_ai_api_key()
    safe_settings["verification_ai_enabled"] = settings_repo.get_verification_ai_enabled()
    safe_settings["verification_ai_base_url"] = settings_repo.get_verification_ai_base_url()
    safe_settings["verification_ai_model"] = settings_repo.get_verification_ai_model()
    safe_settings["verification_ai_api_key_set"] = bool(verification_ai_api_key_value)
    safe_settings["verification_ai_api_key_masked"] = (
        _mask_secret_value(verification_ai_api_key_value) if verification_ai_api_key_value else ""
    )

    # P1：公网模式安全配置
    safe_settings["external_api_public_mode"] = settings_repo.get_external_api_public_mode()
    safe_settings["external_api_ip_whitelist"] = settings_repo.get_external_api_ip_whitelist()
    safe_settings["external_api_rate_limit_per_minute"] = settings_repo.get_external_api_rate_limit()
    safe_settings["external_api_disable_raw_content"] = settings_repo.get_external_api_disable_raw_content()
    safe_settings["external_api_disable_wait_message"] = settings_repo.get_external_api_disable_wait_message()
    safe_settings["external_api_disable_pool_claim_random"] = settings_repo.get_external_api_disable_pool_claim_random()
    safe_settings["external_api_disable_pool_claim_release"] = settings_repo.get_external_api_disable_pool_claim_release()
    safe_settings["external_api_disable_pool_claim_complete"] = settings_repo.get_external_api_disable_pool_claim_complete()
    safe_settings["external_api_disable_pool_stats"] = settings_repo.get_external_api_disable_pool_stats()
    safe_settings["pool_external_enabled"] = settings_repo.get_pool_external_enabled()
    safe_settings["pool_default_provider"] = settings_repo.get_pool_default_provider(strict=False) or "auto"
    safe_settings["active_mailbox_providers"] = settings_repo.get_active_mailbox_provider_names(strict=False)
    safe_settings["active_mailbox_provider_env"] = "ACTIVE_MAILBOX_PROVIDERS"

    # Telegram 推送配置
    tg_bot_token_raw = all_settings.get("telegram_bot_token", "")
    if tg_bot_token_raw and is_encrypted(tg_bot_token_raw):
        try:
            plain_token = decrypt_data(tg_bot_token_raw)
            safe_settings["telegram_bot_token"] = "****" + plain_token[-4:] if len(plain_token) > 4 else "****"
        except Exception:
            safe_settings["telegram_bot_token"] = "****"
    else:
        safe_settings["telegram_bot_token"] = ""
    safe_settings["telegram_chat_id"] = all_settings.get("telegram_chat_id", "")
    safe_settings["telegram_poll_interval"] = _coerce_int_range(
        all_settings.get("telegram_poll_interval", "600") or "600",
        600,
        minimum=10,
        maximum=86400,
    )
    safe_settings["telegram_proxy_url"] = settings_repo.get_telegram_proxy_url()

    # Watchtower 一键更新配置
    wt_url_raw = all_settings.get("watchtower_url", "")
    safe_settings["watchtower_url"] = wt_url_raw or ""
    wt_token_raw = all_settings.get("watchtower_token", "")
    if wt_token_raw and is_encrypted(wt_token_raw):
        try:
            plain_token = decrypt_data(wt_token_raw)
            safe_settings["watchtower_token"] = "****" + plain_token[-4:] if len(plain_token) > 4 else "****"
        except Exception:
            safe_settings["watchtower_token"] = "****"
    else:
        safe_settings["watchtower_token"] = ""

    # 更新方式配置（watchtower / docker_api）
    update_method = all_settings.get("update_method", "watchtower")
    safe_settings["update_method"] = update_method if update_method in ["watchtower", "docker_api"] else "watchtower"

    # 读取 ui_layout_v2 布局状态
    ui_layout = settings_repo.get_ui_layout_v2()
    if not ui_layout or ui_layout.get("version") != 2:
        ui_layout = {
            "version": 2,
            "sidebar": {"collapsed": False},
            "mailbox": {"groupPanelWidth": 220, "accountPanelWidth": 280},
            "tempEmails": {"listPanelWidth": 300},
        }
    safe_settings["ui_layout_v2"] = ui_layout

    response = {"success": True, "settings": safe_settings}
    # 同时在顶层暴露 telegram 字段（兼容前端直接访问）
    response["telegram_bot_token"] = safe_settings.get("telegram_bot_token", "")
    response["telegram_chat_id"] = safe_settings.get("telegram_chat_id", "")
    response["telegram_poll_interval"] = safe_settings.get("telegram_poll_interval", 600)

    return jsonify(response)


@login_required
def api_get_external_api_key_plaintext() -> Any:
    api_key_value = settings_repo.get_external_api_key()
    if not api_key_value:
        return _json_error(
            "EXTERNAL_API_KEY_NOT_SET",
            "当前未设置对外 API Key",
            status=404,
            message_en="External API key is not configured",
        )

    log_audit("copy_external_api_key", "settings", None, "复制对外 API Key 明文")
    return jsonify({"success": True, "api_key": api_key_value})


@login_required
def api_external_api_contract_check() -> Any:
    """Return a local-only external API contract validation report for admins."""
    return jsonify({"success": True, "contract_check": get_external_api_contract_check()})
