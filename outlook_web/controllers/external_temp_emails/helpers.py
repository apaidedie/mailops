from __future__ import annotations

import copy
from typing import Any

from flask import jsonify, request

from outlook_web.security.auth import api_key_required, get_external_api_consumer
from outlook_web.security.external_api_guard import check_feature_enabled, external_api_guards
from outlook_web.repositories import settings as settings_repo
from outlook_web.services import external_api as external_api_service
from outlook_web.services.external_request_limits import CALLER_ID_MAX_LEN, DETAIL_MAX_LEN, TASK_ID_MAX_LEN
from outlook_web.services.mailbox_catalog import MailboxCatalogError, list_unified_mailboxes
from outlook_web.services.provider_catalog import (
    ACTIVE_MAILBOX_PROVIDER_ENV,
    DEPLOYMENT_ENV_CONTRACT,
    EXTERNAL_POOL_DEFAULT_PROVIDER_ENV,
    MAILBOX_SESSION_CLOSE_ENDPOINT,
    MAILBOX_SESSION_READ_ENDPOINT,
    MAILBOX_SESSION_START_ENDPOINT,
    TEMP_MAIL_PROVIDER_ENV,
    get_active_mailbox_provider_filter_contract,
    get_external_api_endpoint_map,
    get_external_mailbox_read_contract,
    get_external_integration_manifest,
    get_mailbox_provider_deployment_profile,
    get_mailbox_provider_catalog,
    get_mailbox_provider_diagnostics,
    get_mailbox_provider_health,
    get_mailbox_provider_preflight,
    get_mailbox_provider_readiness_summary,
    get_mailbox_provider_selection_policy,
    get_provider_documentation_contract,
    get_provider_integration_guide,
    get_provider_alias_contract,
    get_operator_temp_mail_default_provider,
    mailbox_session_provider_metadata,
    PROVIDER_HEALTH_ENDPOINT,
    PROVIDER_PREFLIGHT_ENDPOINT,
    temp_mail_provider_config_status,
    temp_mail_provider_label,
    get_external_api_compatibility_contract,
)
from outlook_web.services.pool import PoolServiceError, claim_random, complete_claim, release_claim
from outlook_web.services.temp_mail_service import TempMailError, get_temp_mail_service

from .constants import temp_mail_service

def _audit(endpoint: str, status: str, *, details: dict[str, Any], email_addr: str = "") -> None:
    external_api_service.audit_external_api_access(
        action="external_api_access",
        email_addr=email_addr,
        endpoint=endpoint,
        status=status,
        details=details,
    )

def _forbidden(endpoint: str, *, email_addr: str = "", reason: str = "consumer_mismatch"):
    _audit(endpoint, "error", details={"code": "FORBIDDEN", "reason": reason}, email_addr=email_addr)
    return jsonify(external_api_service.fail("FORBIDDEN", "当前 API Key 无权操作该任务邮箱", data={"reason": reason})), 403

def _json_object_body(endpoint: str, *, email_addr: str = ""):
    body = request.get_json(silent=True)
    if body is None:
        return {}, None
    if not isinstance(body, dict):
        _audit(endpoint, "error", details={"code": "INVALID_PARAM", "reason": "json_body_not_object"}, email_addr=email_addr)
        return {}, (jsonify(external_api_service.fail("INVALID_PARAM", "请求体必须是 JSON 对象")), 400)
    return body, None

def _validate_required_workflow_fields(body: dict[str, Any]) -> tuple[str, str]:
    caller_id = str(body.get("caller_id") or "").strip()
    task_id = str(body.get("task_id") or "").strip()
    if not caller_id:
        raise external_api_service.InvalidParamError("caller_id 不能为空")
    if not task_id:
        raise external_api_service.InvalidParamError("task_id 不能为空")
    if len(caller_id) > CALLER_ID_MAX_LEN:
        raise external_api_service.InvalidParamError(f"caller_id 不能超过 {CALLER_ID_MAX_LEN} 字符")
    if len(task_id) > TASK_ID_MAX_LEN:
        raise external_api_service.InvalidParamError(f"task_id 不能超过 {TASK_ID_MAX_LEN} 字符")
    return caller_id, task_id

def _pool_error_code(error_code: str) -> str:
    return str(error_code or "INTERNAL_ERROR").upper()

def _consumer_can_use_pool(consumer: dict[str, Any]) -> bool:
    return bool(consumer.get("is_legacy")) or bool(consumer.get("pool_access"))

def _strategy_uses_pool(strategy: str) -> bool:
    return strategy in {"pool_first", "task_temp_first", "pool_only"}

def _pool_disabled_response(endpoint: str):
    if not settings_repo.get_pool_external_enabled():
        _audit(endpoint, "error", details={"code": "FEATURE_DISABLED", "feature": "external_pool"})
        return (
            "external_pool_disabled",
            (
                jsonify(
                    external_api_service.fail(
                        "FEATURE_DISABLED",
                        "功能 external_pool 当前未启用",
                        data={"feature": "external_pool"},
                    )
                ),
                403,
            ),
        )
    if settings_repo.get_external_api_public_mode() and settings_repo.get_external_api_disable_pool_claim_random():
        _audit(endpoint, "error", details={"code": "FEATURE_DISABLED", "feature": "pool_claim_random"})
        return (
            "pool_claim_random_disabled",
            (
                jsonify(
                    external_api_service.fail(
                        "FEATURE_DISABLED",
                        "功能 pool_claim_random 在公网模式下已禁用",
                        data={"feature": "pool_claim_random"},
                    )
                ),
                403,
            ),
        )
    return "", None

def _feature_disabled_response(endpoint: str, feature: str):
    _audit(endpoint, "error", details={"code": "FEATURE_DISABLED", "feature": feature})
    return (
        jsonify(
            external_api_service.fail(
                "FEATURE_DISABLED",
                f"功能 {feature} 在公网模式下已禁用",
                data={"feature": feature},
            )
        ),
        403,
    )

def _pool_close_disabled_response(endpoint: str, close_action: str):
    if not settings_repo.get_pool_external_enabled():
        _audit(endpoint, "error", details={"code": "FEATURE_DISABLED", "feature": "external_pool"})
        return (
            jsonify(
                external_api_service.fail(
                    "FEATURE_DISABLED",
                    "功能 external_pool 当前未启用",
                    data={"feature": "external_pool"},
                )
            ),
            403,
        )
    if not settings_repo.get_external_api_public_mode():
        return None
    if close_action == "release_claim" and settings_repo.get_external_api_disable_pool_claim_release():
        return _feature_disabled_response(endpoint, "pool_claim_release")
    if close_action == "complete_claim" and settings_repo.get_external_api_disable_pool_claim_complete():
        return _feature_disabled_response(endpoint, "pool_claim_complete")
    return None

def _account_id_from_body(body: dict[str, Any], endpoint: str):
    account_id = body.get("account_id")
    if account_id is None:
        _audit(endpoint, "error", details={"code": "ACCOUNT_ID_MISSING"})
        return None, (jsonify(external_api_service.fail("ACCOUNT_ID_MISSING", "account_id 不能为空")), 400)
    try:
        return int(account_id), None
    except (TypeError, ValueError):
        _audit(endpoint, "error", details={"code": "ACCOUNT_ID_INVALID"})
        return None, (jsonify(external_api_service.fail("ACCOUNT_ID_INVALID", "account_id 必须为整数")), 400)

def _pool_session_payload(account: dict[str, Any]) -> dict[str, Any]:
    metadata = mailbox_session_provider_metadata(account)
    contract = get_external_mailbox_read_contract(lifecycle="pool_claim")
    endpoints = get_external_api_endpoint_map()
    return {
        "session_type": "pool_claim",
        "email": str(account.get("email") or ""),
        "provider": metadata["provider"],
        "provider_label": metadata["provider_label"],
        "read_capability": metadata["read_capability"],
        "created_at": str(account.get("claimed_at") or ""),
        "lifecycle": {
            "type": "pool_claim",
            "account_id": account.get("id"),
            "claim_token": str(account.get("claim_token") or ""),
            "claimed_at": str(account.get("claimed_at") or ""),
            "lease_expires_at": str(account.get("lease_expires_at") or ""),
            "complete_endpoint": endpoints["pool_claim_complete"],
            "release_endpoint": endpoints["pool_claim_release"],
        },
        "external_mailbox_read_contract": contract,
        "next_actions": copy.deepcopy(contract.get("next_actions") or {}),
    }

def _task_temp_session_payload(mailbox: dict[str, Any]) -> dict[str, Any]:
    provider_name = str(mailbox.get("provider_name") or "").strip()
    metadata = mailbox_session_provider_metadata(
        {"provider": provider_name, "account_type": "temp_mail", "session_type": "task_temp_mailbox"}
    )
    contract = get_external_mailbox_read_contract(lifecycle="task_temp_mailbox")
    endpoints = get_external_api_endpoint_map()
    return {
        "session_type": "task_temp_mailbox",
        "email": str(mailbox.get("email") or ""),
        "provider": metadata["provider"],
        "provider_label": str(mailbox.get("provider_label") or metadata["provider_label"]),
        "read_capability": str(mailbox.get("read_capability") or metadata["read_capability"]),
        "created_at": str(mailbox.get("created_at") or ""),
        "lifecycle": {
            "type": "task_temp_mailbox",
            "task_token": str(mailbox.get("task_token") or ""),
            "finish_endpoint": endpoints["temp_mail_finish"],
            "visible_in_ui": False,
            "status": str(mailbox.get("status") or ""),
        },
        "external_mailbox_read_contract": contract,
        "next_actions": copy.deepcopy(contract.get("next_actions") or {}),
    }

def _int_body_field(body: dict[str, Any], name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = body.get(name, default)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise external_api_service.InvalidParamError(f"{name} 参数无效") from exc
    if minimum is not None and value < minimum:
        raise external_api_service.InvalidParamError(f"{name} 参数无效")
    if maximum is not None and value > maximum:
        raise external_api_service.InvalidParamError(f"{name} 参数无效")
    return value

def _optional_since_minutes(body: dict[str, Any], *, default: int | None = None) -> int | None:
    raw = body.get("since_minutes", None)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise external_api_service.InvalidParamError("since_minutes 参数无效") from exc
    if value < 1:
        raise external_api_service.InvalidParamError("since_minutes 参数无效")
    return value

def _session_read_params(body: dict[str, Any], *, default_since_minutes: int | None = None) -> dict[str, Any]:
    folder = str(body.get("folder") or "inbox").strip().lower() or "inbox"
    if folder not in {"inbox", "junkemail", "deleteditems"}:
        raise external_api_service.InvalidParamError("folder 参数无效")
    return {
        "folder": folder,
        "skip": _int_body_field(body, "skip", 0, minimum=0),
        "top": _int_body_field(body, "top", 20, minimum=1, maximum=50),
        "from_contains": str(body.get("from_contains") or "").strip(),
        "subject_contains": str(body.get("subject_contains") or "").strip(),
        "since_minutes": _optional_since_minutes(body, default=default_since_minutes),
    }

def _resolve_session_read_target(body: dict[str, Any], consumer: dict[str, Any], endpoint: str) -> tuple[str, int | None]:
    session_type = str(body.get("session_type") or "").strip().lower()
    email_addr = str(body.get("email") or "").strip() or None
    if session_type == "pool_claim":
        claim_token = str(body.get("claim_token") or "").strip()
        if not claim_token:
            raise external_api_service.InvalidParamError("claim_token 不能为空")
        return external_api_service.resolve_external_mail_scope(email_addr, claim_token)

    task_token = str(body.get("task_token") or "").strip()
    if not task_token:
        raise external_api_service.InvalidParamError("task_token 不能为空")
    mailbox = temp_mail_service.get_task_mailbox(task_token)
    if not mailbox:
        raise external_api_service.TaskTokenInvalidError("任务令牌无效", data={"reason": "task_token_invalid"})
    resolved_email = str(mailbox.get("email") or "").strip()
    if email_addr and email_addr.lower() != resolved_email.lower():
        raise external_api_service.InvalidParamError("task_token 与 email 不一致")
    if str(mailbox.get("consumer_key") or "").strip() != str(consumer.get("consumer_key") or "").strip():
        raise external_api_service.EmailScopeForbiddenError(
            "当前 API Key 无权访问该邮箱",
            data={"email": resolved_email, "consumer_id": consumer.get("id"), "consumer_name": consumer.get("name")},
        )
    return external_api_service.resolve_external_mail_scope(resolved_email, None)

def _session_read_payload(
    *,
    session_type: str,
    read_action: str,
    email_addr: str,
    result: dict[str, Any],
    status: str = "ok",
) -> dict[str, Any]:
    return {
        "session_type": session_type,
        "read_action": read_action,
        "email": email_addr,
        "status": status,
        "result": result,
    }

def _read_messages_result(email_addr: str, params: dict[str, Any], baseline_timestamp: int | None) -> dict[str, Any]:
    emails, _method = external_api_service.list_messages_for_external(
        email_addr=email_addr,
        folder=params["folder"],
        skip=params["skip"],
        top=params["top"],
    )
    filtered = external_api_service.filter_messages(
        emails,
        from_contains=params["from_contains"],
        subject_contains=params["subject_contains"],
        since_minutes=params["since_minutes"],
        baseline_timestamp=baseline_timestamp,
    )
    return {"emails": filtered, "count": len(filtered), "has_more": False}

def _read_session_action(
    *,
    read_action: str,
    body: dict[str, Any],
    email_addr: str,
    baseline_timestamp: int | None,
) -> tuple[dict[str, Any], int]:
    default_since = 10 if read_action in {"verification_code", "verification_link"} else None
    params = _session_read_params(body, default_since_minutes=default_since)

    if read_action == "messages":
        return _read_messages_result(email_addr, params, baseline_timestamp), 200

    if read_action == "latest_message":
        return (
            external_api_service.get_latest_message_for_external(
                email_addr=email_addr,
                folder=params["folder"],
                from_contains=params["from_contains"],
                subject_contains=params["subject_contains"],
                since_minutes=params["since_minutes"],
                baseline_timestamp=baseline_timestamp,
            ),
            200,
        )

    if read_action in {"message_detail", "message_raw"}:
        message_id = str(body.get("message_id") or "").strip()
        if read_action == "message_raw":
            feature_resp = check_feature_enabled("raw_content")
            if feature_resp is not None:
                raise external_api_service.FeatureDisabledError("功能 raw_content 在公网模式下已禁用", data={"feature": "raw_content"})
        detail = external_api_service.get_message_detail_for_external(
            email_addr=email_addr,
            message_id=message_id,
            folder=params["folder"],
        )
        if read_action == "message_detail":
            return detail, 200
        return {"id": message_id, "email_address": email_addr, "raw_content": detail.get("raw_content", ""), "method": detail.get("method", "")}, 200

    if read_action in {"verification_code", "verification_link"}:
        code_source = str(body.get("code_source") or "all").strip().lower()
        if code_source not in {"subject", "content", "html", "all"}:
            raise external_api_service.InvalidParamError("code_source 参数无效")
        expected_field = "verification_code" if read_action == "verification_code" else "verification_link"
        result = external_api_service.get_verification_result(
            email_addr=email_addr,
            folder=params["folder"],
            from_contains=params["from_contains"],
            subject_contains=params["subject_contains"],
            since_minutes=params["since_minutes"],
            code_regex=str(body.get("code_regex") or "").strip() or None,
            code_length=str(body.get("code_length") or "").strip() or None,
            code_source=code_source,
            baseline_timestamp=baseline_timestamp,
            apply_default_code_length=read_action == "verification_code",
            expected_field=expected_field,
        )
        if read_action == "verification_code" and not result.get("verification_code"):
            raise external_api_service.VerificationCodeNotFoundError("未找到符合条件的验证码邮件")
        if read_action == "verification_link" and not result.get("verification_link"):
            raise external_api_service.VerificationLinkNotFoundError("未找到符合条件的验证链接邮件")
        return result, 200

    feature_resp = check_feature_enabled("wait_message")
    if feature_resp is not None:
        raise external_api_service.FeatureDisabledError("功能 wait_message 在公网模式下已禁用", data={"feature": "wait_message"})
    timeout_seconds = _int_body_field(body, "timeout_seconds", 30)
    poll_interval = _int_body_field(body, "poll_interval", 5)
    mode = str(body.get("mode") or "sync").strip().lower() or "sync"
    if mode == "async":
        return (
            external_api_service.create_probe(
                email_addr=email_addr,
                timeout_seconds=timeout_seconds,
                poll_interval=poll_interval,
                folder=params["folder"],
                from_contains=params["from_contains"],
                subject_contains=params["subject_contains"],
                since_minutes=params["since_minutes"],
                baseline_timestamp=baseline_timestamp,
            ),
            202,
        )
    if mode != "sync":
        raise external_api_service.InvalidParamError("mode 参数无效")
    return (
        external_api_service.wait_for_message(
            email_addr=email_addr,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval,
            folder=params["folder"],
            from_contains=params["from_contains"],
            subject_contains=params["subject_contains"],
            since_minutes=params["since_minutes"],
            baseline_timestamp=baseline_timestamp,
        ),
        200,
    )

def _external_error_response(exc: external_api_service.ExternalApiError):
    code = str(getattr(exc, "code", "INTERNAL_ERROR") or "INTERNAL_ERROR")
    status = int(getattr(exc, "status", 500) or 500)
    return jsonify(external_api_service.fail(code, str(getattr(exc, "message", str(exc)) or str(exc)), data=exc.data)), status

def _start_pool_session(body: dict[str, Any]) -> dict[str, Any]:
    provider = body.get("provider")
    if "provider" in body and provider is None:
        provider = ""
    account = claim_random(
        caller_id=str(body.get("caller_id") or "").strip(),
        task_id=str(body.get("task_id") or "").strip(),
        provider=provider,
        project_key=body.get("project_key"),
        email_domain=body.get("email_domain"),
    )
    return _pool_session_payload(account)

def _start_task_temp_session(body: dict[str, Any], consumer: dict[str, Any]) -> dict[str, Any]:
    mailbox = temp_mail_service.apply_task_mailbox(
        consumer_key=str(consumer.get("consumer_key") or ""),
        caller_id=str(body.get("caller_id") or "").strip(),
        task_id=str(body.get("task_id") or "").strip(),
        prefix=str(body.get("prefix") or "").strip() or None,
        domain=str(body.get("domain") or "").strip() or None,
        provider_name=str(body.get("provider_name") or "").strip() or None,
    )
    return _task_temp_session_payload(mailbox)

def _close_pool_session(body: dict[str, Any], consumer: dict[str, Any], endpoint: str):
    if not _consumer_can_use_pool(consumer):
        return _forbidden(endpoint, reason="pool_access_required")
    result = str(body.get("result") or "").strip()
    close_action = "release_claim" if result == "release" else "complete_claim"
    disabled_resp = _pool_close_disabled_response(endpoint, close_action)
    if disabled_resp is not None:
        return disabled_resp

    account_id, invalid_account_resp = _account_id_from_body(body, endpoint)
    if invalid_account_resp is not None:
        return invalid_account_resp

    if close_action == "release_claim":
        release_claim(
            account_id=account_id,
            claim_token=str(body.get("claim_token") or ""),
            caller_id=str(body.get("caller_id") or ""),
            task_id=str(body.get("task_id") or ""),
            reason=body.get("reason") if "reason" in body else body.get("detail"),
        )
        payload = {
            "session_type": "pool_claim",
            "close_action": "release_claim",
            "status": "closed",
            "account_id": account_id,
            "pool_status": "available",
        }
    else:
        new_status = complete_claim(
            account_id=account_id,
            claim_token=str(body.get("claim_token") or ""),
            caller_id=str(body.get("caller_id") or ""),
            task_id=str(body.get("task_id") or ""),
            result=result,
            detail=body.get("detail"),
        )
        payload = {
            "session_type": "pool_claim",
            "close_action": "complete_claim",
            "status": "closed",
            "account_id": account_id,
            "pool_status": new_status,
        }

    _audit(
        endpoint,
        "ok",
        details={
            "session_type": "pool_claim",
            "close_action": payload["close_action"],
            "account_id": account_id,
            "pool_status": payload["pool_status"],
        },
    )
    return jsonify(external_api_service.ok(payload))

def _close_task_temp_session(body: dict[str, Any], consumer: dict[str, Any], endpoint: str):
    task_token = str(body.get("task_token") or "").strip()
    mailbox = temp_mail_service.get_task_mailbox(task_token)
    if not mailbox:
        _audit(endpoint, "error", details={"code": "TASK_TOKEN_INVALID", "task_token": task_token}, email_addr="")
        return jsonify(external_api_service.fail("TASK_TOKEN_INVALID", "任务令牌无效")), 404

    email_addr = str(mailbox.get("email") or "")
    if str(mailbox.get("consumer_key") or "").strip() != str(consumer.get("consumer_key") or "").strip():
        return _forbidden(endpoint, email_addr=email_addr)

    result_text = str(body.get("result") or "").strip()
    detail_text = str(body.get("detail") or "").strip()
    if len(result_text) > DETAIL_MAX_LEN or len(detail_text) > DETAIL_MAX_LEN:
        _audit(endpoint, "error", details={"code": "INVALID_PARAM", "task_token": task_token}, email_addr=email_addr)
        return jsonify(external_api_service.fail("INVALID_PARAM", f"result/detail 不能超过 {DETAIL_MAX_LEN} 字符")), 400

    result = temp_mail_service.finish_task_mailbox(task_token)
    cancelled = external_api_service.cancel_pending_probes_for_email(
        str(result.get("email") or ""),
        error_message="探测因任务邮箱 finish 而被取消",
    )
    payload = {
        "session_type": "task_temp_mailbox",
        "close_action": "finish_task_mailbox",
        "status": "closed",
        "task_token": task_token,
        "email": str(result.get("email") or email_addr),
    }
    _audit(
        endpoint,
        "ok",
        details={
            "session_type": "task_temp_mailbox",
            "close_action": "finish_task_mailbox",
            "task_token": task_token,
            "cancelled_probes": cancelled,
            "result": result_text,
            "detail": detail_text[:200],
        },
        email_addr=payload["email"],
    )
    return jsonify(external_api_service.ok(payload))
