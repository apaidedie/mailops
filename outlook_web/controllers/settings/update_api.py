from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from flask import jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.db import get_db
from outlook_web.errors import build_error_payload
from outlook_web.repositories import external_api_keys as external_api_keys_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.security.auth import login_required
from outlook_web.security.crypto import (
    decrypt_data,
    encrypt_data,
    hash_password,
    is_encrypted,
)
from outlook_web.services import webhook_push
from outlook_web.services.external_api_contract_check import get_external_api_contract_check
from outlook_web.services.provider_catalog import get_mailbox_provider_catalog, temp_mail_provider_label
from outlook_web.services.verification_extractor import probe_verification_ai_runtime

from .helpers import _ensure_email_service_available, _is_valid_notification_email, _json_error, _mask_secret_value, _parse_allowed_emails_input, _parse_bool_input, _parse_emailnator_email_types_input, _parse_mailbox_provider_list_input, _parse_temp_mail_domains_input, _parse_temp_mail_prefix_rules_input, _plugin_settings_contract

# ==================== 设置 API ====================

@login_required
def api_update_settings() -> Any:
    """更新设置"""
    # 延迟导入避免循环依赖
    from flask import current_app

    from outlook_web.services import email_push
    from outlook_web.services import graph as graph_service
    from outlook_web.services import scheduler as scheduler_service

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return _json_error(
            "LEGACY_ERROR",
            "请求体必须是 JSON 对象",
            message_en="Request body must be a JSON object",
        )

    updated = []
    errors = []
    scheduler_reload_needed = False
    pending_operations: list[Any] = []

    def queue_setting_update(key: str, value: str) -> None:
        pending_operations.append(lambda key=key, value=value: settings_repo.set_setting(key, value, commit=False))

    def queue_operation(op: Any) -> None:
        pending_operations.append(op)

    current_email_notification_enabled = settings_repo.get_setting("email_notification_enabled", "false").lower() == "true"
    current_email_notification_recipient = settings_repo.get_setting("email_notification_recipient", "").strip()
    target_email_notification_enabled = current_email_notification_enabled
    target_email_notification_recipient = current_email_notification_recipient

    current_webhook_notification_enabled = settings_repo.get_webhook_notification_enabled()
    current_webhook_notification_url = settings_repo.get_webhook_notification_url()
    current_webhook_notification_token = settings_repo.get_webhook_notification_token()
    target_webhook_notification_enabled = current_webhook_notification_enabled
    target_webhook_notification_url = current_webhook_notification_url

    # 验证码 AI 系统级配置（用于 save-time 完整性校验）
    current_verification_ai_enabled = settings_repo.get_verification_ai_enabled()
    current_verification_ai_base_url = settings_repo.get_verification_ai_base_url()
    current_verification_ai_model = settings_repo.get_verification_ai_model()
    current_verification_ai_api_key = settings_repo.get_verification_ai_api_key()
    target_verification_ai_enabled = current_verification_ai_enabled
    target_verification_ai_base_url = current_verification_ai_base_url
    target_verification_ai_model = current_verification_ai_model
    target_verification_ai_api_key = current_verification_ai_api_key

    if "email_notification_enabled" in data:
        target_email_notification_enabled = _parse_bool_input(
            data.get("email_notification_enabled"),
            default=current_email_notification_enabled,
        )
    if "email_notification_recipient" in data:
        target_email_notification_recipient = str(data.get("email_notification_recipient") or "").strip()

    if "email_notification_enabled" in data or "email_notification_recipient" in data:
        if target_email_notification_enabled and not target_email_notification_recipient:
            return _json_error(
                "EMAIL_NOTIFICATION_RECIPIENT_REQUIRED",
                "请填写接收通知邮箱",
                message_en="Please provide a notification recipient email address",
            )
        if target_email_notification_recipient and not _is_valid_notification_email(target_email_notification_recipient):
            return _json_error(
                "EMAIL_NOTIFICATION_RECIPIENT_INVALID",
                "接收通知邮箱格式无效",
                message_en="Invalid notification recipient email address",
            )
        if target_email_notification_enabled:
            try:
                _ensure_email_service_available()
            except email_push.EmailPushError as exc:
                return _json_error(
                    exc.code,
                    exc.message,
                    status=exc.status,
                    message_en=exc.message_en,
                    details=exc.details,
                )
        if "email_notification_enabled" in data:
            queue_setting_update(
                "email_notification_enabled",
                "true" if target_email_notification_enabled else "false",
            )
            updated.append("邮件通知开关")
            scheduler_reload_needed = True
        if "email_notification_recipient" in data:
            queue_setting_update("email_notification_recipient", target_email_notification_recipient)
            updated.append("邮件通知接收邮箱")
            scheduler_reload_needed = True

    if "webhook_notification_enabled" in data:
        target_webhook_notification_enabled = _parse_bool_input(
            data.get("webhook_notification_enabled"),
            default=current_webhook_notification_enabled,
        )
    if "webhook_notification_url" in data:
        target_webhook_notification_url = str(data.get("webhook_notification_url") or "").strip()

    if "webhook_notification_enabled" in data or "webhook_notification_url" in data or "webhook_notification_token" in data:
        if target_webhook_notification_enabled and not target_webhook_notification_url:
            return _json_error(
                "WEBHOOK_URL_REQUIRED",
                "启用 Webhook 通知时必须填写 Webhook URL",
                message_en="Webhook URL is required when webhook notification is enabled",
            )

        if target_webhook_notification_url:
            try:
                webhook_push.validate_webhook_url(target_webhook_notification_url)
            except webhook_push.WebhookPushError as exc:
                return _json_error(
                    exc.code,
                    exc.message,
                    status=exc.status,
                    message_en=exc.message_en,
                    details=exc.details,
                )

        if "webhook_notification_enabled" in data:
            queue_setting_update(
                "webhook_notification_enabled",
                "true" if target_webhook_notification_enabled else "false",
            )
            updated.append("Webhook 通知开关")

        if "webhook_notification_url" in data:
            queue_setting_update("webhook_notification_url", target_webhook_notification_url)
            updated.append("Webhook URL")

        if "webhook_notification_token" in data:
            new_webhook_token = str(data.get("webhook_notification_token") or "").strip()
            if (
                new_webhook_token
                and current_webhook_notification_token
                and new_webhook_token == _mask_secret_value(current_webhook_notification_token)
            ):
                updated.append("Webhook Token（未变更）")
            elif new_webhook_token:
                queue_setting_update("webhook_notification_token", encrypt_data(new_webhook_token))
                updated.append("Webhook Token")
            else:
                queue_setting_update("webhook_notification_token", "")
                updated.append("Webhook Token（已清空）")

    # 更新登录密码
    if "login_password" in data:
        new_password = data["login_password"].strip()
        if new_password:
            if not config.get_allow_login_password_change():
                return _json_error(
                    "LOGIN_PASSWORD_CHANGE_DISABLED",
                    "当前站点已禁用登录密码修改",
                    status=403,
                    message_en="Login password changes are disabled on this site",
                )
            if len(new_password) < 8:
                errors.append("密码长度至少为 8 位")
            else:
                # 哈希新密码
                hashed_password = hash_password(new_password)
                queue_setting_update("login_password", hashed_password)
                updated.append("登录密码")

    # 更新临时邮箱配置
    if "temp_mail_provider" in data:
        try:
            provider = settings_repo.validate_temp_mail_provider_name(data["temp_mail_provider"])
        except ValueError:
            return _json_error(
                "TEMP_MAIL_PROVIDER_INVALID",
                "临时邮箱 Provider 配置无效",
                status=400,
                message_en="Invalid temp mail provider",
            )
        queue_setting_update("temp_mail_provider", provider)
        updated.append("临时邮箱 Provider")

    for setting_key, field in _plugin_settings_contract().items():
        if setting_key not in data:
            continue
        next_value = str(data.get(setting_key) or "").strip()
        current_value = settings_repo.get_setting(setting_key, "")
        if field["secret"] and current_value and next_value == _mask_secret_value(current_value):
            updated.append(f"{setting_key}（未变更）")
        elif field["secret"] and not next_value:
            updated.append(f"{setting_key}（空值已忽略）")
        else:
            queue_setting_update(setting_key, next_value)
            updated.append(setting_key)

    if "temp_mail_api_base_url" in data:
        queue_setting_update(
            "temp_mail_api_base_url",
            settings_repo.normalize_temp_mail_api_base_url(data["temp_mail_api_base_url"]),
        )
        updated.append("临时邮箱 API 地址")

    if "temp_mail_api_key" in data:
        new_api_key = str(data["temp_mail_api_key"] or "").strip()
        existing_api_key = settings_repo.get_temp_mail_api_key()
        if new_api_key and existing_api_key and new_api_key == _mask_secret_value(existing_api_key):
            updated.append("临时邮箱 API Key（未变更）")
        elif new_api_key:
            queue_setting_update("temp_mail_api_key", new_api_key)
            queue_setting_update("gptmail_api_key", new_api_key)
            updated.append("临时邮箱 API Key")
        else:
            updated.append("临时邮箱 API Key（空值已忽略）")

    if "temp_mail_domains" in data:
        try:
            domains = _parse_temp_mail_domains_input(data["temp_mail_domains"])
            queue_setting_update("temp_mail_domains", json.dumps(domains, ensure_ascii=False))
            updated.append("临时邮箱可用域名")
        except ValueError as exc:
            errors.append(str(exc))
        except (TypeError, json.JSONDecodeError):
            errors.append("temp_mail_domains 格式无效")

    if "temp_mail_default_domain" in data:
        queue_setting_update(
            "temp_mail_default_domain",
            str(data["temp_mail_default_domain"] or "").strip(),
        )
        updated.append("临时邮箱默认域名")

    if "temp_mail_prefix_rules" in data:
        try:
            prefix_rules = _parse_temp_mail_prefix_rules_input(data["temp_mail_prefix_rules"])
            queue_setting_update("temp_mail_prefix_rules", json.dumps(prefix_rules, ensure_ascii=False))
            updated.append("临时邮箱前缀规则")
        except ValueError as exc:
            errors.append(str(exc))
        except (TypeError, json.JSONDecodeError):
            errors.append("temp_mail_prefix_rules 格式无效")

    # v0.3: CF Worker 独立域名配置（Tab 重构）
    if "cf_worker_domains" in data:
        try:
            domains = _parse_temp_mail_domains_input(data["cf_worker_domains"])
            queue_setting_update("cf_worker_domains", json.dumps(domains, ensure_ascii=False))
            updated.append("CF Worker 可用域名")
        except ValueError as exc:
            errors.append(str(exc))
        except (TypeError, json.JSONDecodeError):
            errors.append("cf_worker_domains 格式无效")

    if "cf_worker_default_domain" in data:
        queue_setting_update(
            "cf_worker_default_domain",
            str(data["cf_worker_default_domain"] or "").strip(),
        )
        updated.append("CF Worker 默认域名")

    if "cf_worker_prefix_rules" in data:
        try:
            cf_prefix_rules = _parse_temp_mail_prefix_rules_input(data["cf_worker_prefix_rules"])
            queue_setting_update(
                "cf_worker_prefix_rules",
                json.dumps(cf_prefix_rules, ensure_ascii=False),
            )
            updated.append("CF Worker 前缀规则")
        except ValueError as exc:
            errors.append(str(exc))
        except (TypeError, json.JSONDecodeError):
            errors.append("cf_worker_prefix_rules 格式无效")

    # Cloudflare Worker 独立配置（与兼容临时邮箱桥接设置完全隔离）
    if "cf_worker_base_url" in data:
        queue_setting_update("cf_worker_base_url", str(data["cf_worker_base_url"] or "").strip())
        updated.append("CF Worker 地址")

    if "cf_worker_admin_key" in data:
        new_cf_key = str(data["cf_worker_admin_key"] or "").strip()
        existing_cf_key = settings_repo.get_cf_worker_admin_key()
        if new_cf_key and existing_cf_key and new_cf_key == _mask_secret_value(existing_cf_key):
            updated.append("CF Worker Admin Key（未变更）")
        elif new_cf_key:
            # 加密存储（与 telegram_bot_token / external_api_key 保持一致）
            encrypted_cf_key = encrypt_data(new_cf_key)
            queue_setting_update("cf_worker_admin_key", encrypted_cf_key)
            updated.append("CF Worker Admin Key")
        else:
            updated.append("CF Worker Admin Key（空值已忽略）")

    if "emailnator_api_key" in data:
        new_emailnator_key = str(data.get("emailnator_api_key") or "").strip()
        existing_emailnator_key = settings_repo.get_emailnator_api_key()
        if (
            new_emailnator_key
            and existing_emailnator_key
            and new_emailnator_key == _mask_secret_value(existing_emailnator_key)
        ):
            updated.append("Emailnator RapidAPI Key（未变更）")
        elif new_emailnator_key:
            queue_setting_update("emailnator_api_key", encrypt_data(new_emailnator_key))
            updated.append("Emailnator RapidAPI Key")
        else:
            updated.append("Emailnator RapidAPI Key（空值已忽略）")

    if "emailnator_email_types" in data:
        try:
            emailnator_types = _parse_emailnator_email_types_input(data.get("emailnator_email_types"))
            queue_setting_update("emailnator_email_types", json.dumps(emailnator_types, ensure_ascii=False))
            updated.append("Emailnator 邮箱类型")
        except ValueError as exc:
            errors.append(str(exc))
        except (TypeError, json.JSONDecodeError):
            errors.append("emailnator_email_types 格式无效")

    if "duckmail_api_base" in data:
        queue_setting_update("duckmail_api_base", str(data.get("duckmail_api_base") or "").strip().rstrip("/"))
        updated.append("DuckMail API 地址")

    if "duckmail_bearer_token" in data:
        new_duckmail_token = str(data.get("duckmail_bearer_token") or "").strip()
        existing_duckmail_token = settings_repo.get_duckmail_bearer_token()
        if (
            new_duckmail_token
            and existing_duckmail_token
            and new_duckmail_token == _mask_secret_value(existing_duckmail_token)
        ):
            updated.append("DuckMail Bearer Token（未变更）")
        elif new_duckmail_token:
            queue_setting_update("duckmail_bearer_token", encrypt_data(new_duckmail_token))
            updated.append("DuckMail Bearer Token")
        else:
            updated.append("DuckMail Bearer Token（空值已忽略）")

    if "tempmail_lol_api_key" in data:
        new_tempmail_lol_key = str(data.get("tempmail_lol_api_key") or "").strip()
        existing_tempmail_lol_key = settings_repo.get_tempmail_lol_api_key()
        if (
            new_tempmail_lol_key
            and existing_tempmail_lol_key
            and new_tempmail_lol_key == _mask_secret_value(existing_tempmail_lol_key)
        ):
            updated.append("TempMail.lol API Key（未变更）")
        elif new_tempmail_lol_key:
            encrypted_tempmail_lol_key = encrypt_data(new_tempmail_lol_key)
            queue_setting_update("tempmail_lol_api_key", encrypted_tempmail_lol_key)
            queue_setting_update("temp_mail_lol_api_key", encrypted_tempmail_lol_key)
            updated.append("TempMail.lol API Key")
        else:
            updated.append("TempMail.lol API Key（空值已忽略）")

    # 更新 gptmail_api_key（兼容旧字段）
    if "gptmail_api_key" in data:
        new_api_key = str(data["gptmail_api_key"] or "").strip()
        existing_api_key = settings_repo.get_temp_mail_api_key()
        if new_api_key and existing_api_key and new_api_key == _mask_secret_value(existing_api_key):
            updated.append("兼容旧版临时邮箱 API Key 字段（未变更）")
        elif new_api_key:
            queue_setting_update("gptmail_api_key", new_api_key)
            updated.append("兼容旧版临时邮箱 API Key 字段（已更新）")
        else:
            # legacy 字段仅做兼容，不允许空值反向清空正式 temp_mail_api_key。
            updated.append("兼容旧版临时邮箱 API Key 字段（空值已忽略）")

    # 更新对外开放 API Key（建议加密存储）
    if "external_api_key" in data:
        new_external_api_key = str(data["external_api_key"] or "").strip()
        existing_external_api_key = settings_repo.get_external_api_key()
        if (
            new_external_api_key
            and existing_external_api_key
            and new_external_api_key == _mask_secret_value(existing_external_api_key)
        ):
            updated.append("对外 API Key（未变更）")
        elif new_external_api_key:
            encrypted_key = encrypt_data(new_external_api_key)
            queue_setting_update("external_api_key", encrypted_key)
            updated.append("对外 API Key")
        else:
            queue_setting_update("external_api_key", "")
            updated.append("对外 API Key（已清空）")

    # 验证码 AI 增强（系统级）
    if "verification_ai_enabled" in data:
        target_verification_ai_enabled = _parse_bool_input(
            data.get("verification_ai_enabled"),
            default=current_verification_ai_enabled,
        )
        queue_setting_update(
            "verification_ai_enabled",
            "true" if target_verification_ai_enabled else "false",
        )
        updated.append("验证码 AI 开关")

    if "verification_ai_base_url" in data:
        target_verification_ai_base_url = str(data.get("verification_ai_base_url") or "").strip()
        queue_setting_update("verification_ai_base_url", target_verification_ai_base_url)
        updated.append("验证码 AI Base URL")

    if "verification_ai_model" in data:
        target_verification_ai_model = str(data.get("verification_ai_model") or "").strip()
        queue_setting_update("verification_ai_model", target_verification_ai_model)
        updated.append("验证码 AI 模型 ID")

    if "verification_ai_api_key" in data:
        new_verification_ai_api_key = str(data.get("verification_ai_api_key") or "").strip()
        existing_verification_ai_api_key = settings_repo.get_verification_ai_api_key()
        if (
            new_verification_ai_api_key
            and existing_verification_ai_api_key
            and new_verification_ai_api_key == _mask_secret_value(existing_verification_ai_api_key)
        ):
            target_verification_ai_api_key = existing_verification_ai_api_key
            updated.append("验证码 AI API Key（未变更）")
        elif new_verification_ai_api_key:
            target_verification_ai_api_key = new_verification_ai_api_key
            encrypted_key = encrypt_data(new_verification_ai_api_key)
            queue_setting_update("verification_ai_api_key", encrypted_key)
            updated.append("验证码 AI API Key")
        else:
            target_verification_ai_api_key = ""
            queue_setting_update("verification_ai_api_key", "")
            updated.append("验证码 AI API Key（已清空）")

    if target_verification_ai_enabled:
        missing_fields: list[str] = []
        if not target_verification_ai_base_url:
            missing_fields.append("verification_ai_base_url")
        if not target_verification_ai_api_key:
            missing_fields.append("verification_ai_api_key")
        if not target_verification_ai_model:
            missing_fields.append("verification_ai_model")
        if missing_fields:
            return _json_error(
                "VERIFICATION_AI_CONFIG_INCOMPLETE",
                "验证码 AI 已开启，请完整填写 Base URL、API Key、模型 ID",
                message_en="Verification AI is enabled. Please provide Base URL, API Key, and Model ID",
                details={"missing_fields": missing_fields},
            )

    # P2：对外 API 多 Key 配置
    if "external_api_keys" in data:
        raw_items = data["external_api_keys"]
        if not isinstance(raw_items, list):
            errors.append("external_api_keys 必须是数组")
        else:
            existing_keys = {
                int(item["id"]): item for item in external_api_keys_repo.list_external_api_keys(include_disabled=True)
            }
            normalized_items: list[dict[str, Any]] = []
            seen_names: set[str] = set()
            for index, item in enumerate(raw_items):
                if not isinstance(item, dict):
                    errors.append(f"external_api_keys[{index}] 必须是对象")
                    continue

                key_id_raw = item.get("id")
                key_id = None
                if key_id_raw not in (None, ""):
                    try:
                        key_id = int(key_id_raw)
                    except (ValueError, TypeError):
                        errors.append(f"external_api_keys[{index}].id 无效")
                        continue
                    if key_id not in existing_keys:
                        errors.append(f"external_api_keys[{index}].id 不存在")
                        continue

                name = str(item.get("name") or "").strip()
                if not name:
                    errors.append(f"external_api_keys[{index}].name 不能为空")
                    continue
                name_key = name.lower()
                if name_key in seen_names:
                    errors.append(f"external_api_keys[{index}].name 重复")
                    continue
                seen_names.add(name_key)

                api_key_value = item.get("api_key")
                if api_key_value is not None:
                    api_key_value = str(api_key_value).strip()

                if key_id is None and not api_key_value:
                    errors.append(f"external_api_keys[{index}].api_key 不能为空")
                    continue

                existing = existing_keys.get(key_id) if key_id is not None else None
                if existing and api_key_value == existing.get("api_key_masked"):
                    api_key_value = None

                allowed_emails = _parse_allowed_emails_input(item.get("allowed_emails"))
                if item.get("allowed_emails") not in (None, "", []) and not allowed_emails:
                    errors.append(f"external_api_keys[{index}].allowed_emails 至少包含一个合法邮箱")
                    continue

                normalized_items.append(
                    {
                        "id": key_id,
                        "name": name,
                        "api_key": api_key_value,
                        "allowed_emails": allowed_emails,
                        "pool_access": _parse_bool_input(item.get("pool_access"), default=False),
                        "enabled": _parse_bool_input(item.get("enabled"), default=True),
                    }
                )

            if not errors:
                queue_operation(
                    lambda normalized_items=normalized_items: external_api_keys_repo.replace_external_api_keys(
                        normalized_items, commit=False
                    )
                )
                updated.append("对外 API 多 Key 配置")

    # P1：公网模式安全配置
    if "external_api_public_mode" in data:
        val = str(data["external_api_public_mode"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_public_mode", val)
            updated.append("对外 API 公网模式")
        else:
            errors.append("公网模式必须是 true 或 false")

    if "external_api_ip_whitelist" in data:
        raw = data["external_api_ip_whitelist"]
        if isinstance(raw, list):
            whitelist_str = json.dumps(raw, ensure_ascii=False)
        else:
            whitelist_str = str(raw).strip()
        # 简单校验 JSON 数组格式
        try:
            parsed = json.loads(whitelist_str)
            if not isinstance(parsed, list):
                errors.append("IP 白名单必须是 JSON 数组格式")
            else:
                queue_setting_update("external_api_ip_whitelist", whitelist_str)
                updated.append("对外 API IP 白名单")
        except (json.JSONDecodeError, TypeError):
            errors.append("IP 白名单格式无效（应为 JSON 数组）")

    if "external_api_rate_limit_per_minute" in data:
        try:
            limit = int(data["external_api_rate_limit_per_minute"])
            if limit < 1 or limit > 10000:
                errors.append("限流阈值必须在 1-10000 之间")
            else:
                queue_setting_update("external_api_rate_limit_per_minute", str(limit))
                updated.append("对外 API 限流阈值")
        except (ValueError, TypeError):
            errors.append("限流阈值必须是数字")

    if "external_api_disable_raw_content" in data:
        val = str(data["external_api_disable_raw_content"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_disable_raw_content", val)
            updated.append("对外 API 禁用 raw 端点")
        else:
            errors.append("禁用 raw 端点必须是 true 或 false")

    if "external_api_disable_wait_message" in data:
        val = str(data["external_api_disable_wait_message"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_disable_wait_message", val)
            updated.append("对外 API 禁用 wait-message 端点")
        else:
            errors.append("禁用 wait-message 端点必须是 true 或 false")

    if "pool_external_enabled" in data:
        val = str(data["pool_external_enabled"]).lower()
        if val in ("true", "false"):
            queue_setting_update("pool_external_enabled", val)
            updated.append("external pool 总开关")
        else:
            errors.append("external pool 总开关必须是 true 或 false")

    if "pool_default_provider" in data:
        raw_provider = str(data.get("pool_default_provider") or "").strip().lower()
        if not raw_provider or raw_provider == "auto":
            queue_setting_update("pool_default_provider", "")
            updated.append("external pool 默认 provider")
        else:
            from outlook_web.services.provider_catalog import get_mailbox_provider_catalog, get_provider_alias_contract

            catalog_provider_names = {
                str(item.get("provider") or "").strip().lower()
                for item in get_mailbox_provider_catalog()
                if str(item.get("provider") or "").strip()
            }
            alias_provider_names = set((get_provider_alias_contract().get("pool_claim_provider_aliases") or {}).keys())
            if raw_provider in catalog_provider_names or raw_provider in alias_provider_names:
                queue_setting_update("pool_default_provider", raw_provider)
                updated.append("external pool 默认 provider")
            else:
                errors.append("external pool 默认 provider 无效")

    if "active_mailbox_providers" in data:
        active_provider_names = _parse_mailbox_provider_list_input(data.get("active_mailbox_providers"))
        if not active_provider_names:
            queue_setting_update("active_mailbox_providers", "")
            updated.append("启用邮箱来源")
        else:
            from outlook_web.services.provider_catalog import get_mailbox_provider_catalog, get_provider_alias_contract

            catalog_provider_names = {
                str(item.get("provider") or "").strip().lower()
                for item in get_mailbox_provider_catalog(include_inactive=True)
                if str(item.get("provider") or "").strip()
            }
            alias_provider_names = set((get_provider_alias_contract().get("pool_claim_provider_aliases") or {}).keys())
            invalid_provider_names = [
                provider
                for provider in active_provider_names
                if provider not in catalog_provider_names and provider not in alias_provider_names
            ]
            if invalid_provider_names:
                errors.append("启用邮箱来源包含无效 provider: " + ", ".join(invalid_provider_names))
            else:
                queue_setting_update("active_mailbox_providers", json.dumps(active_provider_names, ensure_ascii=False))
                updated.append("启用邮箱来源")

    if "external_api_disable_pool_claim_random" in data:
        val = str(data["external_api_disable_pool_claim_random"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_disable_pool_claim_random", val)
            updated.append("对外 API 禁用 pool claim-random")
        else:
            errors.append("禁用 pool claim-random 必须是 true 或 false")

    if "external_api_disable_pool_claim_release" in data:
        val = str(data["external_api_disable_pool_claim_release"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_disable_pool_claim_release", val)
            updated.append("对外 API 禁用 pool claim-release")
        else:
            errors.append("禁用 pool claim-release 必须是 true 或 false")

    if "external_api_disable_pool_claim_complete" in data:
        val = str(data["external_api_disable_pool_claim_complete"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_disable_pool_claim_complete", val)
            updated.append("对外 API 禁用 pool claim-complete")
        else:
            errors.append("禁用 pool claim-complete 必须是 true 或 false")

    if "external_api_disable_pool_stats" in data:
        val = str(data["external_api_disable_pool_stats"]).lower()
        if val in ("true", "false"):
            queue_setting_update("external_api_disable_pool_stats", val)
            updated.append("对外 API 禁用 pool stats")
        else:
            errors.append("禁用 pool stats 必须是 true 或 false")

    # 更新刷新周期
    if "refresh_interval_days" in data:
        try:
            days = int(data["refresh_interval_days"])
            if days < 1 or days > 90:
                errors.append("刷新周期必须在 1-90 天之间")
            else:
                queue_setting_update("refresh_interval_days", str(days))
                updated.append("刷新周期")
        except ValueError:
            errors.append("刷新周期必须是数字")

    # 更新刷新间隔
    if "refresh_delay_seconds" in data:
        try:
            seconds = int(data["refresh_delay_seconds"])
            if seconds < 0 or seconds > 60:
                errors.append("刷新间隔必须在 0-60 秒之间")
            else:
                queue_setting_update("refresh_delay_seconds", str(seconds))
                updated.append("刷新间隔")
        except ValueError:
            errors.append("刷新间隔必须是数字")

    # 更新 Cron 表达式
    if "refresh_cron" in data:
        cron_expr = data["refresh_cron"].strip()
        if cron_expr:
            try:
                from croniter import croniter

                croniter(cron_expr, datetime.now())
                queue_setting_update("refresh_cron", cron_expr)
                updated.append("Cron 表达式")
                scheduler_reload_needed = True
            except ImportError:
                errors.append("croniter 库未安装")
            except Exception as e:
                errors.append(f"Cron 表达式无效: {str(e)}")

    # 更新刷新策略
    if "use_cron_schedule" in data:
        use_cron = str(data["use_cron_schedule"]).lower()
        if use_cron in ("true", "false"):
            queue_setting_update("use_cron_schedule", use_cron)
            updated.append("刷新策略")
            scheduler_reload_needed = True
        else:
            errors.append("刷新策略必须是 true 或 false")

    # 更新定时刷新开关
    if "enable_scheduled_refresh" in data:
        enable = str(data["enable_scheduled_refresh"]).lower()
        if enable in ("true", "false"):
            queue_setting_update("enable_scheduled_refresh", enable)
            updated.append("定时刷新开关")
            scheduler_reload_needed = True
        else:
            errors.append("定时刷新开关必须是 true 或 false")

    # 更新轮询配置
    if "enable_auto_polling" in data:
        enable_polling = str(data["enable_auto_polling"]).lower()
        if enable_polling in ("true", "false"):
            queue_setting_update("enable_auto_polling", enable_polling)
            updated.append("自动轮询开关")
        else:
            errors.append("自动轮询开关必须是 true 或 false")

    if "polling_interval" in data:
        try:
            interval = int(data["polling_interval"])
            if interval < 3 or interval > 300:
                errors.append("轮询间隔必须在 3-300 秒之间")
            else:
                queue_setting_update("polling_interval", str(interval))
                updated.append("轮询间隔")
        except ValueError:
            errors.append("轮询间隔必须是数字")

    if "polling_count" in data:
        try:
            count = int(data["polling_count"])
            if count < 0 or count > 100:
                errors.append("轮询次数必须在 0-100 次之间（0 表示持续轮询）")
            else:
                queue_setting_update("polling_count", str(count))
                updated.append("轮询次数")
        except ValueError:
            errors.append("轮询次数必须是数字")

    # [Phase 3 deprecated] 简洁模式自动轮询配置 — 保留写入，向后兼容
    if "enable_compact_auto_poll" in data:
        enable_compact = str(data["enable_compact_auto_poll"]).lower()
        if enable_compact in ("true", "false"):
            queue_setting_update("enable_compact_auto_poll", enable_compact)
            updated.append("简洁轮询开关")
        else:
            errors.append("简洁模式自动轮询开关必须是 true 或 false")

    if "compact_poll_interval" in data:
        try:
            compact_interval = int(data["compact_poll_interval"])
            if compact_interval < 3 or compact_interval > 60:
                errors.append("简洁模式轮询间隔必须在 3-60 秒之间")
            else:
                queue_setting_update("compact_poll_interval", str(compact_interval))
                updated.append("简洁轮询间隔")
        except (ValueError, TypeError):
            errors.append("简洁模式轮询间隔必须是数字")

    if "compact_poll_max_count" in data:
        try:
            compact_max_count = int(data["compact_poll_max_count"])
            if compact_max_count < 0 or compact_max_count > 100:
                errors.append("简洁模式最多轮询次数必须在 0-100 之间")
            else:
                queue_setting_update("compact_poll_max_count", str(compact_max_count))
                updated.append("简洁轮询次数")
        except (ValueError, TypeError):
            errors.append("简洁模式最多轮询次数必须是数字")

    # Telegram 推送配置
    if "telegram_poll_interval" in data:
        try:
            tg_interval = int(data["telegram_poll_interval"])
            if tg_interval < 10 or tg_interval > 86400:
                errors.append("Telegram 轮询间隔必须在 10-86400 秒之间")
            else:
                queue_setting_update("telegram_poll_interval", str(tg_interval))
                updated.append("Telegram 轮询间隔")
                scheduler_reload_needed = True
        except (ValueError, TypeError):
            errors.append("Telegram 轮询间隔必须是数字")

    if "telegram_bot_token" in data:
        tg_token = str(data["telegram_bot_token"]).strip()
        if tg_token and not tg_token.startswith("****"):
            encrypted_token = encrypt_data(tg_token)
            queue_setting_update("telegram_bot_token", encrypted_token)
            updated.append("Telegram Bot Token")
        elif not tg_token:
            queue_setting_update("telegram_bot_token", "")
            updated.append("Telegram Bot Token（已清空）")
        else:
            # 脱敏占位符（****xxx），跳过不覆盖
            updated.append("Telegram Bot Token（未变更）")

    if "telegram_chat_id" in data:
        tg_chat_id = str(data["telegram_chat_id"]).strip()
        queue_setting_update("telegram_chat_id", tg_chat_id)
        updated.append("Telegram Chat ID")

    if "telegram_proxy_url" in data:
        tg_proxy = str(data["telegram_proxy_url"]).strip()
        queue_setting_update("telegram_proxy_url", tg_proxy)
        updated.append("Telegram 代理地址")

    # Watchtower 一键更新配置
    if "watchtower_url" in data:
        wt_url = str(data["watchtower_url"]).strip()
        queue_setting_update("watchtower_url", wt_url)
        updated.append("Watchtower URL")

    if "watchtower_token" in data:
        wt_token = str(data["watchtower_token"]).strip()
        if wt_token and wt_token != "" and not wt_token.startswith("****"):
            encrypted_wt_token = encrypt_data(wt_token)
            queue_setting_update("watchtower_token", encrypted_wt_token)
            updated.append("Watchtower Token")
        elif not wt_token:
            queue_setting_update("watchtower_token", "")
            updated.append("Watchtower Token（已清空）")
        else:
            # 脱敏占位符（****xxx），跳过不覆盖
            updated.append("Watchtower Token（未变更）")

    # 更新方式配置（watchtower / docker_api）
    if "update_method" in data:
        method = str(data["update_method"]).strip().lower()
        if method in ["watchtower", "docker_api"]:
            queue_setting_update("update_method", method)
            updated.append("更新方式")
        else:
            errors.append(f"不支持的更新方式: {method} （仅支持 watchtower / docker_api）")

    # 更新 ui_layout_v2 布局状态
    if "ui_layout_v2" in data:
        new_layout = data["ui_layout_v2"]
        if not isinstance(new_layout, dict):
            errors.append("ui_layout_v2 必须是 JSON 对象")
        elif new_layout.get("version") != 2:
            errors.append("ui_layout_v2.version 必须为 2")
        else:
            queue_setting_update("ui_layout_v2", json.dumps(new_layout, ensure_ascii=False))
            updated.append("界面布局状态")

    if errors:
        return _json_error(
            "LEGACY_ERROR",
            "；".join(errors),
            message_en="Invalid settings payload",
        )

    if updated:
        db = get_db()
        try:
            db.execute("BEGIN")
            for op in pending_operations:
                result = op()
                if result is False:
                    raise RuntimeError("settings_update_failed")
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return _json_error(
                "INTERNAL_ERROR",
                "设置保存失败，请重试",
                status=500,
                message_en="Failed to save settings. Please try again",
            )

        scheduler_reloaded = None
        email_notification_just_enabled = (not current_email_notification_enabled) and target_email_notification_enabled
        webhook_notification_just_enabled = (not current_webhook_notification_enabled) and target_webhook_notification_enabled
        if email_notification_just_enabled:
            try:
                from outlook_web.services import notification_dispatch

                notification_dispatch.bootstrap_channel_cursors(notification_dispatch.CHANNEL_EMAIL)
            except Exception:
                pass
        if webhook_notification_just_enabled:
            try:
                from outlook_web.services import notification_dispatch

                notification_dispatch.bootstrap_channel_cursors(notification_dispatch.CHANNEL_WEBHOOK)
            except Exception:
                pass

        if scheduler_reload_needed:
            try:
                scheduler = scheduler_service.get_scheduler_instance()
                if scheduler:
                    # FD-00007 / TDD-00007：调度器 Job 在后台线程运行，必须传入真实 Flask app 实例；
                    # 避免将 current_app(LocalProxy) 直接作为 job 参数，导致后续执行时报“Working outside of application context”。
                    app_obj = current_app._get_current_object()
                    scheduler_service.configure_scheduler_jobs(
                        scheduler,
                        app_obj,
                        graph_service.test_refresh_token_with_rotation,
                    )
                    scheduler_reloaded = True
                else:
                    scheduler_reloaded = False
            except Exception:
                scheduler_reloaded = False

        try:
            details = json.dumps(
                {
                    "updated": updated,
                    "scheduler_reload_needed": scheduler_reload_needed,
                    "scheduler_reloaded": scheduler_reloaded,
                },
                ensure_ascii=False,
            )
        except Exception:
            details = f"updated={','.join(updated)}"
        log_audit("update", "settings", None, details)
        return jsonify(
            {
                "success": True,
                "message": f"已更新：{', '.join(updated)}",
                "message_en": "Settings updated successfully",
                "scheduler_reloaded": scheduler_reloaded,
            }
        )
    else:
        return _json_error(
            "LEGACY_ERROR",
            "没有需要更新的设置",
            message_en="No settings changes were provided",
        )
