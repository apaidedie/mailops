from __future__ import annotations

import copy
from typing import Any

from flask import jsonify, request

from outlook_web.repositories import settings as settings_repo
from outlook_web.security.auth import api_key_required, get_external_api_consumer
from outlook_web.security.external_api_guard import check_feature_enabled, external_api_guards
from outlook_web.services import external_api as external_api_service
from outlook_web.services.external_request_limits import CALLER_ID_MAX_LEN, DETAIL_MAX_LEN, TASK_ID_MAX_LEN
from outlook_web.services.mailbox_catalog import MailboxCatalogError, list_unified_mailboxes
from outlook_web.services.pool import PoolServiceError, claim_random, complete_claim, release_claim
from outlook_web.services.provider_catalog import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    MAILBOX_SESSION_CLOSE_ENDPOINT,
    MAILBOX_SESSION_READ_ENDPOINT,
    MAILBOX_SESSION_START_ENDPOINT,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    TEMP_MAIL_PROVIDER_ENV,
    get_active_mailbox_provider_filter_contract,
    get_external_api_compatibility_contract,
    get_external_api_endpoint_map,
    get_external_integration_manifest,
    get_external_mailbox_read_contract,
    get_mailbox_provider_catalog,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_diagnostics,
    get_mailbox_provider_health,
    get_mailbox_provider_preflight,
    get_mailbox_provider_readiness_summary,
    get_mailbox_provider_selection_policy,
    get_operator_temp_mail_default_provider,
    get_provider_alias_contract,
    get_provider_documentation_contract,
    get_provider_integration_guide,
    mailbox_session_provider_metadata,
    temp_mail_provider_config_status,
    temp_mail_provider_label,
)
from outlook_web.services.temp_mail_service import TempMailError, get_temp_mail_service

from .constants import temp_mail_service
from .helpers import _audit, _forbidden, _json_object_body


@api_key_required
@external_api_guards()
def api_external_apply_temp_email():
    endpoint = "/api/v1/external/temp-emails/apply"
    body, invalid_body_resp = _json_object_body(endpoint)
    if invalid_body_resp is not None:
        return invalid_body_resp
    consumer = get_external_api_consumer() or {}

    try:
        provider_name = str(body.get("provider_name") or "").strip() or None
        mailbox = temp_mail_service.apply_task_mailbox(
            consumer_key=str(consumer.get("consumer_key") or ""),
            caller_id=str(body.get("caller_id") or "").strip(),
            task_id=str(body.get("task_id") or "").strip(),
            prefix=str(body.get("prefix") or "").strip() or None,
            domain=str(body.get("domain") or "").strip() or None,
            provider_name=provider_name,
        )
        payload = {
            "email": mailbox["email"],
            "prefix": mailbox["prefix"],
            "domain": mailbox["domain"],
            "provider_name": mailbox.get("provider_name") or "",
            "provider_label": mailbox.get("provider_label") or "",
            "read_capability": mailbox.get("read_capability") or "temp_provider",
            "task_token": mailbox["task_token"],
            "created_at": mailbox["created_at"],
            "visible_in_ui": False,
            "status": mailbox["status"],
            "external_mailbox_read_contract": get_external_mailbox_read_contract(lifecycle="task_temp_mailbox"),
        }
        _audit(
            endpoint,
            "ok",
            details={
                "task_token": mailbox["task_token"],
                "domain": mailbox["domain"],
                "provider_name": payload["provider_name"],
            },
            email_addr=mailbox["email"],
        )
        return jsonify(external_api_service.ok(payload))
    except TempMailError as exc:
        _audit(endpoint, "error", details={"code": exc.code}, email_addr="")
        return jsonify(external_api_service.fail(exc.code, exc.message, data=exc.data)), exc.status
    except Exception as exc:
        _audit(endpoint, "error", details={"code": "INTERNAL_ERROR", "err": type(exc).__name__}, email_addr="")
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_finish_temp_email(task_token: str):
    endpoint = "/api/v1/external/temp-emails/{task_token}/finish"
    consumer = get_external_api_consumer() or {}
    mailbox = temp_mail_service.get_task_mailbox(task_token)
    if not mailbox:
        _audit(endpoint, "error", details={"code": "TASK_TOKEN_INVALID", "task_token": task_token}, email_addr="")
        return jsonify(external_api_service.fail("TASK_TOKEN_INVALID", "任务令牌无效")), 404

    if str(mailbox.get("consumer_key") or "").strip() != str(consumer.get("consumer_key") or "").strip():
        return _forbidden(endpoint, email_addr=str(mailbox.get("email") or ""))

    body, invalid_body_resp = _json_object_body(endpoint, email_addr=str(mailbox.get("email") or ""))
    if invalid_body_resp is not None:
        return invalid_body_resp
    result_text = str(body.get("result") or "").strip()
    detail_text = str(body.get("detail") or "").strip()
    if len(result_text) > DETAIL_MAX_LEN or len(detail_text) > DETAIL_MAX_LEN:
        _audit(
            endpoint,
            "error",
            details={"code": "INVALID_PARAM", "task_token": task_token},
            email_addr=str(mailbox.get("email") or ""),
        )
        return jsonify(external_api_service.fail("INVALID_PARAM", f"result/detail 不能超过 {DETAIL_MAX_LEN} 字符")), 400

    try:
        result = temp_mail_service.finish_task_mailbox(task_token)
        cancelled = external_api_service.cancel_pending_probes_for_email(
            str(result.get("email") or ""),
            error_message="探测因任务邮箱 finish 而被取消",
        )
        _audit(
            endpoint,
            "ok",
            details={
                "task_token": task_token,
                "cancelled_probes": cancelled,
                "result": result_text,
                "detail": detail_text[:200],
            },
            email_addr=str(result.get("email") or ""),
        )
        return jsonify(
            external_api_service.ok(
                {"task_token": task_token, "status": result["status"], "email": str(result.get("email") or "")}
            )
        )
    except TempMailError as exc:
        _audit(
            endpoint, "error", details={"code": exc.code, "task_token": task_token}, email_addr=str(mailbox.get("email") or "")
        )
        return jsonify(external_api_service.fail(exc.code, exc.message, data=exc.data)), exc.status
    except Exception as exc:
        _audit(
            endpoint,
            "error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__, "task_token": task_token},
            email_addr=str(mailbox.get("email") or ""),
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500
