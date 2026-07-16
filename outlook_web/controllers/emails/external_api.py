from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from flask import current_app, jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.errors import build_error_payload, build_error_response
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import groups as groups_repo
from outlook_web.security.auth import api_key_required, login_required
from outlook_web.security.external_api_guard import external_api_guards
from outlook_web.services import account_compact_summary as compact_summary_service
from outlook_web.services import email_delete as email_delete_service
from outlook_web.services import external_api as external_api_service
from outlook_web.services import graph as graph_service
from outlook_web.services import imap as imap_service
from outlook_web.services import verification_channel_routing as verification_channel_service
from outlook_web.services.imap_generic import (
    get_email_detail_imap_generic_result,
    get_emails_imap_generic,
)
from outlook_web.services.mailbox_resolver import normalize_alias_email

from .helpers import _external_error_response, _parse_external_common_args, _resolve_external_error


@api_key_required
@external_api_guards()
def api_external_get_messages() -> Any:
    try:
        args = _parse_external_common_args()
        emails, method = external_api_service.list_messages_for_external(
            email_addr=args["email"],
            folder=args["folder"],
            skip=args["skip"],
            top=args["top"],
        )
        filtered = external_api_service.filter_messages(
            emails,
            from_contains=args["from_contains"],
            subject_contains=args["subject_contains"],
            since_minutes=args["since_minutes"],
            baseline_timestamp=args.get("baseline_timestamp"),
        )
        external_api_service.record_claim_read_context(
            claim_token=args.get("claim_token"),
            email_addr=args["email"],
        )

        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=args["email"] or "",
            endpoint="/api/v1/external/messages",
            status="ok",
            details={"method": method, "count": len(filtered)},
        )

        return jsonify(external_api_service.ok({"emails": filtered, "count": len(filtered), "has_more": False}))
    except external_api_service.ExternalApiError as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages",
            status="error",
            details={"code": exc.code},
        )
        return _external_error_response(exc)
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_get_latest_message() -> Any:
    try:
        args = _parse_external_common_args()
        latest = external_api_service.get_latest_message_for_external(
            email_addr=args["email"],
            folder=args["folder"],
            from_contains=args["from_contains"],
            subject_contains=args["subject_contains"],
            since_minutes=args["since_minutes"],
            baseline_timestamp=args.get("baseline_timestamp"),
        )
        external_api_service.record_claim_read_context(
            claim_token=args.get("claim_token"),
            email_addr=args["email"],
        )
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=args["email"] or "",
            endpoint="/api/v1/external/messages/latest",
            status="ok",
            details={"method": latest.get("method")},
        )
        return jsonify(external_api_service.ok(latest))
    except external_api_service.ExternalApiError as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages/latest",
            status="error",
            details={"code": exc.code},
        )
        return _external_error_response(exc)
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages/latest",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_get_message_detail(message_id: str) -> Any:
    try:
        args = _parse_external_common_args()
        detail = external_api_service.get_message_detail_for_external(
            email_addr=args["email"],
            message_id=message_id,
            folder=args["folder"],
        )
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=args["email"] or "",
            endpoint="/api/v1/external/messages/{message_id}",
            status="ok",
            details={"method": detail.get("method")},
        )
        return jsonify(external_api_service.ok(detail))
    except external_api_service.ExternalApiError as exc:
        resolved = _resolve_external_error(exc, allow_nested_upstream=True)
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages/{message_id}",
            status="error",
            details={"code": resolved["code"]},
        )
        return _external_error_response(exc, allow_nested_upstream=True)
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages/{message_id}",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards(feature="raw_content")
def api_external_get_message_raw(message_id: str) -> Any:
    try:
        args = _parse_external_common_args()
        detail = external_api_service.get_message_detail_for_external(
            email_addr=args["email"],
            message_id=message_id,
            folder=args["folder"],
        )
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=args["email"] or "",
            endpoint="/api/v1/external/messages/{message_id}/raw",
            status="ok",
            details={"method": detail.get("method")},
        )
        return jsonify(
            external_api_service.ok(
                {
                    "id": message_id,
                    "email_address": args["email"],
                    "raw_content": detail.get("raw_content", ""),
                    "method": detail.get("method", ""),
                }
            )
        )
    except external_api_service.ExternalApiError as exc:
        resolved = _resolve_external_error(exc, allow_nested_upstream=True)
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages/{message_id}/raw",
            status="error",
            details={"code": resolved["code"]},
        )
        return _external_error_response(exc, allow_nested_upstream=True)
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/messages/{message_id}/raw",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_get_verification_code() -> Any:
    try:
        args = _parse_external_common_args(default_since_minutes=10)
        code_length = (request.args.get("code_length") or "").strip() or None
        code_regex = (request.args.get("code_regex") or "").strip() or None
        code_source = (request.args.get("code_source") or "all").strip().lower()
        if code_source not in {"subject", "content", "html", "all"}:
            raise external_api_service.InvalidParamError("code_source 参数无效")

        result = external_api_service.get_verification_result(
            email_addr=args["email"],
            folder=args["folder"],
            from_contains=args["from_contains"],
            subject_contains=args["subject_contains"],
            since_minutes=args["since_minutes"],
            code_regex=code_regex,
            code_length=code_length,
            code_source=code_source,
            baseline_timestamp=args.get("baseline_timestamp"),
            expected_field="verification_code",
        )
        if not result.get("verification_code"):
            raise external_api_service.VerificationCodeNotFoundError("未找到符合条件的验证码邮件")

        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=args["email"] or "",
            endpoint="/api/v1/external/verification-code",
            status="ok",
            details={
                "matched_email_id": result.get("matched_email_id"),
                "method": result.get("method"),
            },
        )
        return jsonify(external_api_service.ok(result))
    except external_api_service.ExternalApiError as exc:
        resolved = _resolve_external_error(exc)
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/verification-code",
            status="error",
            details={"code": resolved["code"]},
        )
        return _external_error_response(exc)
    except ValueError:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/verification-code",
            status="error",
            details={"code": "INVALID_PARAM"},
        )
        return jsonify(external_api_service.fail("INVALID_PARAM", "参数错误")), 400
    except Exception:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/verification-code",
            status="error",
            details={"code": "INTERNAL_ERROR"},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_get_verification_link() -> Any:
    try:
        args = _parse_external_common_args(default_since_minutes=10)
        result = external_api_service.get_verification_result(
            email_addr=args["email"],
            folder=args["folder"],
            from_contains=args["from_contains"],
            subject_contains=args["subject_contains"],
            since_minutes=args["since_minutes"],
            baseline_timestamp=args.get("baseline_timestamp"),
            apply_default_code_length=False,
            expected_field="verification_link",
        )
        if not result.get("verification_link"):
            raise external_api_service.VerificationLinkNotFoundError("未找到符合条件的验证链接邮件")

        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=args["email"] or "",
            endpoint="/api/v1/external/verification-link",
            status="ok",
            details={
                "matched_email_id": result.get("matched_email_id"),
                "method": result.get("method"),
            },
        )
        return jsonify(external_api_service.ok(result))
    except external_api_service.ExternalApiError as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/verification-link",
            status="error",
            details={"code": exc.code},
        )
        return _external_error_response(exc)
    except Exception:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/verification-link",
            status="error",
            details={"code": "INTERNAL_ERROR"},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards(feature="wait_message")
def api_external_wait_message() -> Any:
    try:
        args = _parse_external_common_args()
        timeout_seconds = request.args.get("timeout_seconds", "30")
        poll_interval = request.args.get("poll_interval", "5")
        mode = request.args.get("mode", "sync").lower()

        if mode == "async":
            # P2 异步模式：创建探测请求，立即返回 probe_id
            probe_result = external_api_service.create_probe(
                email_addr=args["email"],
                timeout_seconds=int(timeout_seconds),
                poll_interval=int(poll_interval),
                folder=args["folder"],
                from_contains=args["from_contains"],
                subject_contains=args["subject_contains"],
                since_minutes=args["since_minutes"],
                baseline_timestamp=args.get("baseline_timestamp"),
            )
            external_api_service.audit_external_api_access(
                action="external_api_access",
                email_addr=args["email"] or "",
                endpoint="/api/v1/external/wait-message?mode=async",
                status="ok",
                details={"probe_id": probe_result["probe_id"]},
            )
            return jsonify(external_api_service.ok(probe_result)), 202
        else:
            # P0 同步模式：阻塞等待（向下兼容）
            result = external_api_service.wait_for_message(
                email_addr=args["email"],
                timeout_seconds=int(timeout_seconds),
                poll_interval=int(poll_interval),
                folder=args["folder"],
                from_contains=args["from_contains"],
                subject_contains=args["subject_contains"],
                since_minutes=args["since_minutes"],
                baseline_timestamp=args.get("baseline_timestamp"),
            )
            external_api_service.audit_external_api_access(
                action="external_api_access",
                email_addr=args["email"] or "",
                endpoint="/api/v1/external/wait-message",
                status="ok",
                details={
                    "matched_email_id": result.get("id"),
                    "method": result.get("method"),
                },
            )
            return jsonify(external_api_service.ok(result))
    except external_api_service.ExternalApiError as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/wait-message",
            status="error",
            details={"code": exc.code},
        )
        return _external_error_response(exc)
    except Exception as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=(request.args.get("email") or "").strip(),
            endpoint="/api/v1/external/wait-message",
            status="error",
            details={"code": "INTERNAL_ERROR", "err": type(exc).__name__},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500


@api_key_required
@external_api_guards()
def api_external_get_probe_status(probe_id: str) -> Any:
    """P2: 查询异步探测状态与结果"""
    try:
        result = external_api_service.get_probe_status(probe_id)
        external_api_service.ensure_external_email_access(result.get("email") or "", allow_finished=True)
        if result.get("status") == "cancelled":
            external_api_service.audit_external_api_access(
                action="external_api_access",
                email_addr=result.get("email") or "",
                endpoint="/api/v1/external/probe/{probe_id}",
                status="error",
                details={
                    "code": result.get("error_code") or "PROBE_CANCELLED",
                    "probe_id": probe_id,
                    "probe_status": result.get("status"),
                },
            )
            return (
                jsonify(
                    external_api_service.fail(
                        str(result.get("error_code") or "PROBE_CANCELLED"),
                        str(result.get("error_message") or "探测因任务结束而被取消"),
                        data=result,
                    )
                ),
                409,
            )
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr=result.get("email") or "",
            endpoint="/api/v1/external/probe/{probe_id}",
            status="ok",
            details={"probe_id": probe_id, "probe_status": result.get("status")},
        )
        return jsonify(external_api_service.ok(result))
    except external_api_service.ExternalApiError as exc:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr="",
            endpoint="/api/v1/external/probe/{probe_id}",
            status="error",
            details={"code": exc.code, "probe_id": probe_id},
        )
        return _external_error_response(exc)
    except Exception:
        external_api_service.audit_external_api_access(
            action="external_api_access",
            email_addr="",
            endpoint="/api/v1/external/probe/{probe_id}",
            status="error",
            details={"code": "INTERNAL_ERROR", "probe_id": probe_id},
        )
        return jsonify(external_api_service.fail("INTERNAL_ERROR", "服务内部错误")), 500
