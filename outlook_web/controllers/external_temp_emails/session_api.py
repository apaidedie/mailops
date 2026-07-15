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

from .constants import MAILBOX_SESSION_CLOSE_TYPES, MAILBOX_SESSION_READ_ACTIONS, MAILBOX_SESSION_STRATEGIES
from .helpers import _audit, _close_pool_session, _close_task_temp_session, _consumer_can_use_pool, _external_error_response, _forbidden, _json_object_body, _pool_disabled_response, _pool_error_code, _read_session_action, _resolve_session_read_target, _session_read_payload, _start_pool_session, _start_task_temp_session, _strategy_uses_pool, _validate_required_workflow_fields

@api_key_required
@external_api_guards()
def api_external_start_mailbox_session():
    endpoint = MAILBOX_SESSION_START_ENDPOINT
    body, invalid_body_resp = _json_object_body(endpoint)
    if invalid_body_resp is not None:
        return invalid_body_resp
    consumer = get_external_api_consumer() or {}
    strategy = str(body.get("source_strategy") or "pool_first").strip().lower()
    if strategy not in MAILBOX_SESSION_STRATEGIES:
        _audit(endpoint, "error", details={"code": "INVALID_PARAM", "reason": "invalid_source_strategy"})
        return (
            jsonify(
                external_api_service.fail(
                    "INVALID_PARAM",
                    "source_strategy 无效",
                    data={"allowed_values": sorted(MAILBOX_SESSION_STRATEGIES)},
                )
            ),
            400,
        )
    if _strategy_uses_pool(strategy) and not _consumer_can_use_pool(consumer):
        return _forbidden(endpoint, reason="pool_access_required")

    try:
        if strategy == "task_temp_only":
            payload = _start_task_temp_session(body, consumer)
        elif strategy == "pool_only":
            _reason, disabled_resp = _pool_disabled_response(endpoint)
            if disabled_resp is not None:
                return disabled_resp
            payload = _start_pool_session(body)
        elif strategy == "task_temp_first":
            payload = _start_task_temp_session(body, consumer)
        else:
            reason, disabled_resp = _pool_disabled_response(endpoint)
            if disabled_resp is not None and reason != "external_pool_disabled":
                return disabled_resp
            if disabled_resp is not None:
                payload = _start_task_temp_session(body, consumer)
            else:
                try:
                    payload = _start_pool_session(body)
                except PoolServiceError as exc:
                    if _pool_error_code(exc.error_code) != "NO_AVAILABLE_ACCOUNT":
                        raise
                    payload = _start_task_temp_session(body, consumer)
        _audit(
            endpoint,
            "ok",
            details={
                "session_type": payload.get("session_type") or "",
                "provider": payload.get("provider") or "",
                "source_strategy": strategy,
            },
            email_addr=str(payload.get("email") or ""),
        )
        return jsonify(external_api_service.ok(payload))
    except PoolServiceError as exc:
        code = _pool_error_code(exc.error_code)
        _audit(endpoint, "error", details={"code": code, "source_strategy": strategy}, email_addr="")
        return jsonify(external_api_service.fail(code, str(exc))), exc.http_status
    except TempMailError as exc:
        _audit(endpoint, "error", details={"code": exc.code, "source_strategy": strategy}, email_addr="")
        return jsonify(external_api_service.fail(exc.code, exc.message, data=exc.data)), exc.status
    except Exception as exc:
        _audit(endpoint, "error", details={"code": "INTERNAL_ERROR", "err": type(exc).__name__}, email_addr="")
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500

@api_key_required
@external_api_guards()
def api_external_read_mailbox_session():
    endpoint = MAILBOX_SESSION_READ_ENDPOINT
    body, invalid_body_resp = _json_object_body(endpoint)
    if invalid_body_resp is not None:
        return invalid_body_resp
    consumer = get_external_api_consumer() or {}
    session_type = str(body.get("session_type") or "").strip().lower()
    if session_type not in MAILBOX_SESSION_CLOSE_TYPES:
        _audit(endpoint, "error", details={"code": "INVALID_PARAM", "reason": "invalid_session_type"})
        return (
            jsonify(
                external_api_service.fail(
                    "INVALID_PARAM",
                    "session_type 无效",
                    data={"allowed_values": sorted(MAILBOX_SESSION_CLOSE_TYPES)},
                )
            ),
            400,
        )
    read_action = str(body.get("read_action") or "").strip().lower()
    if read_action not in MAILBOX_SESSION_READ_ACTIONS:
        _audit(endpoint, "error", details={"code": "INVALID_PARAM", "reason": "invalid_read_action"})
        return (
            jsonify(
                external_api_service.fail(
                    "INVALID_PARAM",
                    "read_action 无效",
                    data={"allowed_values": sorted(MAILBOX_SESSION_READ_ACTIONS)},
                )
            ),
            400,
        )
    if session_type == "pool_claim" and not _consumer_can_use_pool(consumer):
        return _forbidden(endpoint, reason="pool_access_required")

    try:
        caller_id, task_id = _validate_required_workflow_fields(body)
        email_addr, baseline_timestamp = _resolve_session_read_target(body, consumer, endpoint)
        result, status_code = _read_session_action(
            read_action=read_action,
            body=body,
            email_addr=email_addr,
            baseline_timestamp=baseline_timestamp,
        )
        if session_type == "pool_claim":
            external_api_service.record_claim_read_context(
                claim_token=str(body.get("claim_token") or "").strip(),
                email_addr=email_addr,
                caller_id=caller_id,
                task_id=task_id,
                detail=f"session read_action={read_action}, email={email_addr}",
            )
        _audit(
            endpoint,
            "ok",
            details={
                "session_type": session_type,
                "read_action": read_action,
                "status_code": status_code,
            },
            email_addr=email_addr,
        )
        return jsonify(
            external_api_service.ok(
                _session_read_payload(
                    session_type=session_type,
                    read_action=read_action,
                    email_addr=email_addr,
                    result=result,
                    status="pending" if status_code == 202 else "ok",
                )
            )
        ), status_code
    except external_api_service.ExternalApiError as exc:
        _audit(
            endpoint,
            "error",
            details={"code": exc.code, "session_type": session_type, "read_action": read_action},
            email_addr=str(body.get("email") or ""),
        )
        return _external_error_response(exc)
    except Exception as exc:
        _audit(
            endpoint,
            "error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__, "session_type": session_type, "read_action": read_action},
            email_addr=str(body.get("email") or ""),
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500

@api_key_required
@external_api_guards()
def api_external_close_mailbox_session():
    endpoint = MAILBOX_SESSION_CLOSE_ENDPOINT
    body, invalid_body_resp = _json_object_body(endpoint)
    if invalid_body_resp is not None:
        return invalid_body_resp
    consumer = get_external_api_consumer() or {}
    session_type = str(body.get("session_type") or "").strip().lower()
    if session_type not in MAILBOX_SESSION_CLOSE_TYPES:
        _audit(endpoint, "error", details={"code": "INVALID_PARAM", "reason": "invalid_session_type"})
        return (
            jsonify(
                external_api_service.fail(
                    "INVALID_PARAM",
                    "session_type 无效",
                    data={"allowed_values": sorted(MAILBOX_SESSION_CLOSE_TYPES)},
                )
            ),
            400,
        )

    try:
        if session_type == "pool_claim":
            return _close_pool_session(body, consumer, endpoint)
        return _close_task_temp_session(body, consumer, endpoint)
    except PoolServiceError as exc:
        code = _pool_error_code(exc.error_code)
        _audit(endpoint, "error", details={"code": code, "session_type": session_type}, email_addr="")
        return jsonify(external_api_service.fail(code, str(exc))), exc.http_status
    except TempMailError as exc:
        _audit(endpoint, "error", details={"code": exc.code, "session_type": session_type}, email_addr="")
        return jsonify(external_api_service.fail(exc.code, exc.message, data=exc.data)), exc.status
    except Exception as exc:
        _audit(endpoint, "error", details={"code": "INTERNAL_ERROR", "err": type(exc).__name__}, email_addr="")
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500
