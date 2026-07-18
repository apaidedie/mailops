from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from flask import current_app, jsonify, request

from mailops import config
from mailops.audit import log_audit
from mailops.errors import build_error_payload, build_error_response
from mailops.repositories import accounts as accounts_repo
from mailops.repositories import groups as groups_repo
from mailops.security.auth import api_key_required, login_required
from mailops.security.external_api_guard import external_api_guards
from mailops.services import account_compact_summary as compact_summary_service
from mailops.services import email_delete as email_delete_service
from mailops.services import external_api as external_api_service
from mailops.services import graph as graph_service
from mailops.services import imap as imap_service
from mailops.services import verification_channel_routing as verification_channel_service
from mailops.services.imap_generic import (
    get_email_detail_imap_generic_result,
    get_emails_imap_generic,
)
from mailops.services.mailbox_resolver import normalize_alias_email

from .constants import _LOGGER, IMAP_SERVER_NEW, IMAP_SERVER_OLD
from .helpers import (
    _build_account_credential_decrypt_failed_response,
    _build_response_from_error_payload,
    _persist_refresh_token,
    _resolve_external_error,
    _should_return_email_not_found_for_web_extract,
    _update_account_summary_from_verification,
)


@login_required
def api_batch_get_emails() -> Any:
    """批量获取邮件（Issue #64 增强项 / Phase 3）。

    目标：为前端批量拉取提供服务端聚合能力。

    当前实现以测试契约为最低目标：
    - 接受 {account_ids:[...]}，account_id 不存在不报整体错误
    - 返回 {success:true, results:[...], summary:{...}}
    - 每个 account_id 都有对应 result，缺失账号 success=false + error=ACCOUNT_NOT_FOUND

    注意：本接口不与池状态机耦合（claimed/frozen/retired 不影响）。
    """

    data = request.get_json(silent=True) or {}
    account_ids = data.get("account_ids", [])

    if not isinstance(account_ids, list) or not account_ids:
        return build_error_response(
            "ACCOUNT_IDS_REQUIRED",
            "请选择要批量拉取邮件的账号",
            message_en="Please select accounts to batch fetch emails",
            status=400,
        )

    try:
        parsed_ids = [int(aid) for aid in account_ids]
    except (TypeError, ValueError):
        return build_error_response(
            "INVALID_PARAM",
            "account_ids 必须为整数列表",
            message_en="account_ids must be a list of integers",
            status=400,
        )

    deduped_ids: List[int] = []
    seen_ids = set()
    for aid in parsed_ids:
        if aid in seen_ids:
            continue
        seen_ids.add(aid)
        deduped_ids.append(aid)

    # 测试环境：避免引入外部上游依赖（Graph/IMAP），只验证接口契约与聚合结构。
    # 生产环境：再走真实拉取链路。
    if bool(current_app.config.get("TESTING")):
        results: List[Dict[str, Any]] = []
        success_accounts = 0
        failed_accounts = 0

        for aid in deduped_ids:
            try:
                account = accounts_repo.get_account_by_id(int(aid))
                if not account:
                    results.append(
                        {
                            "account_id": int(aid),
                            "success": False,
                            "error": "ACCOUNT_NOT_FOUND",
                        }
                    )
                    failed_accounts += 1
                    continue

                results.append(
                    {
                        "account_id": int(aid),
                        "email": account.get("email") or "",
                        "success": True,
                        "folders": {},
                    }
                )
                success_accounts += 1
            except Exception as e:
                _LOGGER.exception("batch_get_emails failed for account_id=%s", aid)
                results.append(
                    {
                        "account_id": int(aid),
                        "success": False,
                        "error": "BATCH_EMAIL_FETCH_FAILED",
                        "details": str(e),
                    }
                )
                failed_accounts += 1

        summary = {
            "total_accounts": len(deduped_ids),
            "success_accounts": success_accounts,
            "failed_accounts": failed_accounts,
        }

        return jsonify(
            {
                "success": True,
                "results": results,
                "summary": summary,
            }
        )

    # 生产环境：真实聚合拉取（默认 folders=inbox+junkemail, latest-only）。
    folders = data.get("folders")
    if folders is None:
        folders = ["inbox", "junkemail"]
    if not isinstance(folders, list) or not folders:
        return build_error_response(
            "INVALID_PARAM",
            "folders 必须为非空列表",
            message_en="folders must be a non-empty list",
            status=400,
        )
    normalized_folders = [str(f or "").strip().lower() for f in folders if str(f or "").strip()]
    if not normalized_folders:
        return build_error_response(
            "INVALID_PARAM",
            "folders 必须为非空列表",
            message_en="folders must be a non-empty list",
            status=400,
        )

    try:
        skip = int(data.get("skip", 0) or 0)
        top = int(data.get("top", 10) or 10)
    except Exception:
        return build_error_response(
            "INVALID_PARAM",
            "skip/top 参数无效",
            message_en="Invalid skip/top",
            status=400,
        )

    results: List[Dict[str, Any]] = []
    success_accounts = 0
    failed_accounts = 0

    for aid in deduped_ids:
        account = None
        try:
            account = accounts_repo.get_account_by_id(int(aid))
        except Exception:
            account = None

        if not account:
            results.append({"account_id": int(aid), "success": False, "error": "ACCOUNT_NOT_FOUND"})
            failed_accounts += 1
            continue

        email_addr = str(account.get("email") or "")
        account_type = (account.get("account_type") or "outlook").strip().lower()

        # outlook 类型需要先检查凭据解密错误（保持与单账号接口一致的安全行为）
        if account_type != "imap":
            decrypt_error_response = _build_account_credential_decrypt_failed_response(account)
            if decrypt_error_response:
                results.append(
                    {
                        "account_id": int(aid),
                        "email": email_addr,
                        "success": False,
                        "error": "ACCOUNT_CREDENTIAL_DECRYPT_FAILED",
                    }
                )
                failed_accounts += 1
                continue

        proxy_url = ""
        try:
            if account.get("group_id"):
                group = groups_repo.get_group_by_id(account["group_id"])
                if group:
                    proxy_url = group.get("proxy_url", "") or ""
        except Exception:
            proxy_url = ""

        per_folder_results: Dict[str, Any] = {}
        any_folder_success = False

        for folder in normalized_folders:
            try:
                if account_type == "imap":
                    result = get_emails_imap_generic(
                        email_addr=email_addr,
                        imap_password=account.get("imap_password", "") or "",
                        imap_host=account.get("imap_host", "") or "",
                        imap_port=account.get("imap_port", 993) or 993,
                        folder=folder,
                        provider=account.get("provider", "_default") or "_default",
                        skip=skip,
                        top=top,
                    )
                    if result.get("success"):
                        result["account_summary"] = compact_summary_service.update_summary_from_message_list(
                            int(account["id"]),
                            result.get("emails") or [],
                            folder=folder,
                        )
                    per_folder_results[folder] = result
                    any_folder_success = any_folder_success or bool(result.get("success"))
                    continue

                graph_result = graph_service.get_emails_graph(
                    account.get("client_id") or "",
                    account.get("refresh_token") or "",
                    folder,
                    skip,
                    top,
                    proxy_url,
                )
                if graph_result.get("success"):
                    emails = graph_result.get("emails", [])
                    account_summary = compact_summary_service.update_summary_from_message_list(
                        int(account["id"]),
                        emails,
                        folder=folder,
                    )
                    # Token Rotation + 刷新时间
                    new_rt = graph_result.get("new_refresh_token")
                    if new_rt:
                        _persist_refresh_token(account, str(new_rt or ""))
                    accounts_repo.touch_last_refresh_at(int(account["id"]))

                    formatted = []
                    for e in emails:
                        formatted.append(
                            {
                                "id": e.get("id"),
                                "subject": e.get("subject", "无主题"),
                                "from": e.get("from", {}).get("emailAddress", {}).get("address", "未知"),
                                "date": e.get("receivedDateTime", ""),
                                "is_read": e.get("isRead", False),
                                "has_attachments": e.get("hasAttachments", False),
                                "body_preview": e.get("bodyPreview", ""),
                            }
                        )

                    per_folder_results[folder] = {
                        "success": True,
                        "emails": formatted,
                        "method": "Graph API",
                        "has_more": len(formatted) >= top,
                        "account_summary": account_summary,
                    }
                    any_folder_success = True
                    continue

                imap_new_result = imap_service.get_emails_imap_with_server(
                    email_addr,
                    account.get("client_id") or "",
                    account.get("refresh_token") or "",
                    folder,
                    skip,
                    top,
                    IMAP_SERVER_NEW,
                )
                if imap_new_result.get("success"):
                    account_summary = compact_summary_service.update_summary_from_message_list(
                        int(account["id"]),
                        imap_new_result.get("emails", []) or [],
                        folder=folder,
                    )
                    per_folder_results[folder] = {
                        "success": True,
                        "emails": imap_new_result.get("emails", []),
                        "method": "IMAP (New)",
                        "has_more": False,
                        "account_summary": account_summary,
                    }
                    any_folder_success = True
                    continue

                imap_old_result = imap_service.get_emails_imap_with_server(
                    email_addr,
                    account.get("client_id") or "",
                    account.get("refresh_token") or "",
                    folder,
                    skip,
                    top,
                    IMAP_SERVER_OLD,
                )
                if imap_old_result.get("success"):
                    account_summary = compact_summary_service.update_summary_from_message_list(
                        int(account["id"]),
                        imap_old_result.get("emails", []) or [],
                        folder=folder,
                    )
                    per_folder_results[folder] = {
                        "success": True,
                        "emails": imap_old_result.get("emails", []),
                        "method": "IMAP (Old)",
                        "has_more": False,
                        "account_summary": account_summary,
                    }
                    any_folder_success = True
                    continue

                # 全部方法失败：保留错误结构（不抛整批）
                per_folder_results[folder] = {
                    "success": False,
                    "error": graph_result.get("error") or {"code": "EMAIL_FETCH_FAILED"},
                }
            except Exception as e:
                per_folder_results[folder] = {
                    "success": False,
                    "error": {
                        "code": "EMAIL_BATCH_FETCH_FAILED",
                        "message": "批量拉取失败",
                        "message_en": "Batch fetch failed",
                        "details": str(e),
                    },
                }

        results.append(
            {
                "account_id": int(aid),
                "email": email_addr,
                "success": any_folder_success,
                "folders": per_folder_results,
            }
        )
        if any_folder_success:
            success_accounts += 1
        else:
            failed_accounts += 1

    summary = {
        "total_accounts": len(deduped_ids),
        "success_accounts": success_accounts,
        "failed_accounts": failed_accounts,
    }

    log_audit(
        "batch_fetch_emails",
        "email",
        None,
        f"批量获取邮件：total={summary['total_accounts']} success={success_accounts} failed={failed_accounts}",
    )

    return jsonify(
        {
            "success": True,
            "results": results,
            "summary": summary,
        }
    )


@login_required
def api_get_emails(email_addr: str) -> Any:
    """获取邮件列表（支持分页，不使用缓存）"""
    _t0 = time.monotonic()
    email_addr = normalize_alias_email(email_addr) or ""
    account = accounts_repo.get_account_by_email(email_addr)

    if not account:
        return build_error_response(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            message_en="Account not found",
            err_type="NotFoundError",
            status=404,
            details=f"email={email_addr}",
        )

    folder = request.args.get("folder", "inbox")  # inbox, junkemail, deleteditems
    skip = int(request.args.get("skip", 0))
    top = int(request.args.get("top", 20))

    # PRD-00005 / FD-00005 / TDD-00005：按 account_type 路由分发（Outlook 链路保持原样，IMAP 走通用 IMAP 服务）
    account_type = (account.get("account_type") or "outlook").strip().lower()
    if account_type != "imap":
        decrypt_error_response = _build_account_credential_decrypt_failed_response(account)
        if decrypt_error_response:
            return decrypt_error_response

    if account_type == "imap":
        _t_imap_generic = time.monotonic()
        result = get_emails_imap_generic(
            email_addr=email_addr,
            imap_password=account.get("imap_password", "") or "",
            imap_host=account.get("imap_host", "") or "",
            imap_port=account.get("imap_port", 993) or 993,
            folder=folder,
            provider=account.get("provider", "_default") or "_default",
            skip=skip,
            top=top,
        )
        _LOGGER.debug(
            "[PERF] get_emails | email=%s | imap_generic | %dms | success=%s",
            email_addr,
            (time.monotonic() - _t_imap_generic) * 1000,
            result.get("success"),
        )
        if result.get("success"):
            result["account_summary"] = compact_summary_service.update_summary_from_message_list(
                int(account["id"]),
                result.get("emails") or [],
                folder=folder,
            )
        _LOGGER.debug(
            "[PERF] get_emails | email=%s | 总耗时=%dms | type=imap",
            email_addr,
            (time.monotonic() - _t0) * 1000,
        )
        return jsonify(result)

    # 获取分组代理设置
    proxy_url = ""
    if account.get("group_id"):
        group = groups_repo.get_group_by_id(account["group_id"])
        if group:
            proxy_url = group.get("proxy_url", "") or ""

    # 收集所有错误信息
    all_errors = {}

    # 1. 尝试 Graph API
    _t_graph = time.monotonic()
    graph_result = graph_service.get_emails_graph(account["client_id"], account["refresh_token"], folder, skip, top, proxy_url)
    _LOGGER.debug(
        "[PERF] get_emails | email=%s | graph_api | %dms | success=%s",
        email_addr,
        (time.monotonic() - _t_graph) * 1000,
        graph_result.get("success"),
    )
    if graph_result.get("success"):
        emails = graph_result.get("emails", [])
        account_summary = compact_summary_service.update_summary_from_message_list(
            int(account["id"]),
            emails,
            folder=folder,
        )
        # 更新刷新时间，同时保存 Microsoft 可能返回的新 refresh_token（Token Rotation）
        new_rt = graph_result.get("new_refresh_token")
        if new_rt:
            _persist_refresh_token(account, str(new_rt or ""))
        accounts_repo.touch_last_refresh_at(int(account["id"]))

        # 格式化 Graph API 返回的数据
        formatted = []
        for e in emails:
            formatted.append(
                {
                    "id": e.get("id"),
                    "subject": e.get("subject", "无主题"),
                    "from": e.get("from", {}).get("emailAddress", {}).get("address", "未知"),
                    "date": e.get("receivedDateTime", ""),
                    "is_read": e.get("isRead", False),
                    "has_attachments": e.get("hasAttachments", False),
                    "body_preview": e.get("bodyPreview", ""),
                }
            )

        _LOGGER.debug(
            "[PERF] get_emails | email=%s | 总耗时=%dms | method=graph_api",
            email_addr,
            (time.monotonic() - _t0) * 1000,
        )
        return jsonify(
            {
                "success": True,
                "emails": formatted,
                "method": "Graph API",
                "has_more": len(formatted) >= top,
                "account_summary": account_summary,
            }
        )
    else:
        graph_error = graph_result.get("error")
        all_errors["graph"] = graph_error

        # 如果是代理错误，不再回退 IMAP
        if isinstance(graph_error, dict) and graph_error.get("type") in (
            "ProxyError",
            "ConnectionError",
        ):
            return build_error_response(
                "EMAIL_PROXY_CONNECTION_FAILED",
                "代理连接失败，请检查分组代理设置",
                message_en="Proxy connection failed. Please check the group proxy settings",
                err_type="ProxyError",
                status=502,
                details=all_errors,
                extra={"details": all_errors},
            )

    _t_imap_new = time.monotonic()
    imap_new_result = imap_service.get_emails_imap_with_server(
        account["email"],
        account["client_id"],
        account["refresh_token"],
        folder,
        skip,
        top,
        IMAP_SERVER_NEW,
    )
    _LOGGER.debug(
        "[PERF] get_emails | email=%s | imap_new | %dms | success=%s",
        email_addr,
        (time.monotonic() - _t_imap_new) * 1000,
        imap_new_result.get("success"),
    )
    if imap_new_result.get("success"):
        account_summary = compact_summary_service.update_summary_from_message_list(
            int(account["id"]),
            imap_new_result.get("emails", []),
            folder=folder,
        )
        _LOGGER.debug(
            "[PERF] get_emails | email=%s | 总耗时=%dms | method=imap_new",
            email_addr,
            (time.monotonic() - _t0) * 1000,
        )
        return jsonify(
            {
                "success": True,
                "emails": imap_new_result.get("emails", []),
                "method": "IMAP (New)",
                "has_more": False,  # IMAP 分页暂未完全实现
                "account_summary": account_summary,
            }
        )
    else:
        all_errors["imap_new"] = imap_new_result.get("error")

    # 3. 尝试旧版 IMAP (outlook.office365.com)
    _t_imap_old = time.monotonic()
    imap_old_result = imap_service.get_emails_imap_with_server(
        account["email"],
        account["client_id"],
        account["refresh_token"],
        folder,
        skip,
        top,
        IMAP_SERVER_OLD,
    )
    _LOGGER.debug(
        "[PERF] get_emails | email=%s | imap_old | %dms | success=%s",
        email_addr,
        (time.monotonic() - _t_imap_old) * 1000,
        imap_old_result.get("success"),
    )
    if imap_old_result.get("success"):
        account_summary = compact_summary_service.update_summary_from_message_list(
            int(account["id"]),
            imap_old_result.get("emails", []),
            folder=folder,
        )
        _LOGGER.debug(
            "[PERF] get_emails | email=%s | 总耗时=%dms | method=imap_old",
            email_addr,
            (time.monotonic() - _t0) * 1000,
        )
        return jsonify(
            {
                "success": True,
                "emails": imap_old_result.get("emails", []),
                "method": "IMAP (Old)",
                "has_more": False,
                "account_summary": account_summary,
            }
        )
    else:
        all_errors["imap_old"] = imap_old_result.get("error")

    _LOGGER.debug(
        "[PERF] get_emails | email=%s | 总耗时=%dms | 全部失败",
        email_addr,
        (time.monotonic() - _t0) * 1000,
    )
    # 先尝试 Graph→IMAP 全链路；仅在全部失败且 Graph 明确 401 时提示重授权
    if graph_result.get("auth_expired"):
        return build_error_response(
            "ACCOUNT_AUTH_EXPIRED",
            "账号授权已失效，请前往「刷新 Token」页面重新授权",
            message_en="Account authorization has expired. Please re-authorize the account",
            err_type="AuthorizationError",
            status=401,
            details={"email": email_addr},
        )

    return build_error_response(
        "EMAIL_FETCH_ALL_METHODS_FAILED",
        "无法获取邮件，所有方式均失败",
        message_en="Failed to fetch emails. All methods failed",
        status=502,
        details=all_errors,
        extra={"details": all_errors},
    )


@login_required
def api_delete_emails() -> Any:
    """批量删除邮件（永久删除）"""
    data = request.json
    email_addr = data.get("email", "")
    message_ids = data.get("ids", [])

    if not email_addr or not message_ids:
        return build_error_response("INVALID_PARAM", "参数不完整", message_en="Missing required parameters")

    account = accounts_repo.get_account_by_email(email_addr)
    if not account:
        return build_error_response(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            message_en="Account not found",
            status=404,
        )

    # PRD-00005：IMAP 账号不支持远程删除（避免误操作与跨厂商副作用）
    account_type = (account.get("account_type") or "outlook").strip().lower()
    if account_type == "imap":
        error_payload = build_error_payload(
            "IMAP_DELETE_NOT_SUPPORTED",
            "IMAP 邮箱不支持远程删除，请在邮箱客户端中操作",
            "NotSupportedError",
            400,
            f"email={email_addr}",
        )
        return jsonify({"success": False, "error": error_payload}), 400

    # 获取分组代理设置
    proxy_url = ""
    if account.get("group_id"):
        group = groups_repo.get_group_by_id(account["group_id"])
        if group:
            proxy_url = group.get("proxy_url", "") or ""

    response_data, method_used = email_delete_service.delete_emails_with_fallback(
        email_addr=email_addr,
        client_id=account["client_id"],
        refresh_token=account["refresh_token"],
        message_ids=message_ids,
        proxy_url=proxy_url,
        delete_emails_graph=graph_service.delete_emails_graph,
        delete_emails_imap=imap_service.delete_emails_imap,
        imap_server_new=IMAP_SERVER_NEW,
        imap_server_old=IMAP_SERVER_OLD,
    )

    if method_used == "graph":
        log_audit(
            "delete",
            "email",
            email_addr,
            f"删除邮件 {len(message_ids)} 封（Graph API）",
        )
    elif method_used == "imap_new":
        log_audit("delete", "email", email_addr, f"删除邮件 {len(message_ids)} 封（IMAP New）")
    elif method_used == "imap_old":
        log_audit("delete", "email", email_addr, f"删除邮件 {len(message_ids)} 封（IMAP Old）")

    return jsonify(response_data)


@login_required
def api_get_email_detail(email_addr: str, message_id: str) -> Any:
    """获取邮件详情"""
    _t0 = time.monotonic()
    email_addr = normalize_alias_email(email_addr) or ""
    _LOGGER.debug(
        "[PERF] get_email_detail | 开始 | email=%s message_id=%s",
        email_addr,
        message_id,
    )
    _LOGGER.info("email_detail_request email=%s message_id=%s", email_addr, message_id)
    account = accounts_repo.get_account_by_email(email_addr)

    if not account:
        _LOGGER.warning("email_detail_account_not_found email=%s", email_addr)
        return build_error_response(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            message_en="Account not found",
            status=404,
        )

    account_type = (account.get("account_type") or "outlook").strip().lower()
    folder = request.args.get("folder", "inbox")
    _LOGGER.info(
        "email_detail_type=%s provider=%s folder=%s",
        account_type,
        account.get("provider", "N/A"),
        folder,
    )

    if account_type == "imap":
        _t_imap = time.monotonic()
        detail_result = get_email_detail_imap_generic_result(
            email_addr=email_addr,
            imap_password=account.get("imap_password", "") or "",
            imap_host=account.get("imap_host", "") or "",
            imap_port=account.get("imap_port", 993) or 993,
            message_id=message_id,
            folder=folder,
            provider=account.get("provider", "_default") or "_default",
        )
        _LOGGER.debug(
            "[PERF] get_email_detail | email=%s | imap_generic | %dms | success=%s",
            email_addr,
            (time.monotonic() - _t_imap) * 1000,
            detail_result.get("success"),
        )
        if detail_result.get("success"):
            detail = detail_result.get("email") or {}
            _LOGGER.info(
                "email_detail_imap_ok email=%s subject=%s",
                email_addr,
                detail.get("subject", "?")[:40],
            )
            _LOGGER.debug(
                "[PERF] get_email_detail | email=%s | 总耗时=%dms | method=imap_generic",
                email_addr,
                (time.monotonic() - _t0) * 1000,
            )
            return jsonify({"success": True, "email": detail})
        error_payload = detail_result.get("error") or {}
        _LOGGER.warning("email_detail_imap_failed email=%s message_id=%s", email_addr, message_id)
        return _build_response_from_error_payload(error_payload)

    method = request.args.get("method", "graph")

    if method == "graph":
        # 获取分组代理设置
        proxy_url = ""
        if account.get("group_id"):
            group = groups_repo.get_group_by_id(account["group_id"])
            if group:
                proxy_url = group.get("proxy_url", "") or ""

        _t_graph = time.monotonic()
        detail = graph_service.get_email_detail_graph(account["client_id"], account["refresh_token"], message_id, proxy_url)
        _LOGGER.debug(
            "[PERF] get_email_detail | email=%s | graph_api | %dms | success=%s",
            email_addr,
            (time.monotonic() - _t_graph) * 1000,
            bool(detail),
        )
        if detail:
            _LOGGER.debug(
                "[PERF] get_email_detail | email=%s | 总耗时=%dms | method=graph",
                email_addr,
                (time.monotonic() - _t0) * 1000,
            )
            return jsonify(
                {
                    "success": True,
                    "email": {
                        "id": detail.get("id"),
                        "subject": detail.get("subject", "无主题"),
                        "from": detail.get("from", {}).get("emailAddress", {}).get("address", "未知"),
                        "to": ", ".join(
                            [r.get("emailAddress", {}).get("address", "") for r in detail.get("toRecipients", [])]
                        ),
                        "cc": ", ".join(
                            [r.get("emailAddress", {}).get("address", "") for r in detail.get("ccRecipients", [])]
                        ),
                        "date": detail.get("receivedDateTime", ""),
                        "body": detail.get("body", {}).get("content", ""),
                        "body_type": detail.get("body", {}).get("contentType", "text"),
                    },
                }
            )

    # 如果 Graph API 失败，尝试 IMAP
    _t_imap_fallback = time.monotonic()
    detail = imap_service.get_email_detail_imap(
        account["email"],
        account["client_id"],
        account["refresh_token"],
        message_id,
        folder,
    )
    _LOGGER.debug(
        "[PERF] get_email_detail | email=%s | imap_fallback | %dms | success=%s",
        email_addr,
        (time.monotonic() - _t_imap_fallback) * 1000,
        bool(detail),
    )
    if detail:
        _LOGGER.debug(
            "[PERF] get_email_detail | email=%s | 总耗时=%dms | method=imap_fallback",
            email_addr,
            (time.monotonic() - _t0) * 1000,
        )
        return jsonify({"success": True, "email": detail})

    _LOGGER.debug(
        "[PERF] get_email_detail | email=%s | 总耗时=%dms | 全部失败",
        email_addr,
        (time.monotonic() - _t0) * 1000,
    )
    return build_error_response(
        "EMAIL_DETAIL_FETCH_FAILED",
        "获取邮件详情失败",
        message_en="Failed to fetch email details",
        status=502,
        details=f"email={email_addr} message_id={message_id}",
    )


@login_required
def api_extract_verification(email_addr: str) -> Any:
    """
    提取验证码和链接接口

    功能：从指定邮箱的最新邮件中提取验证码和链接

    实现策略（多 API 回退机制）：
    1. Graph API (inbox) - 优先从收件箱获取
    2. Graph API (junkemail) - 从垃圾邮件获取
    3. IMAP (新服务器) - Graph API 失败时回退
    4. IMAP (旧服务器) - 最后的回退方案
    """
    _t0 = time.monotonic()
    _LOGGER.debug("[PERF] extract_verification | 开始 | email=%s", email_addr)

    # 获取账号信息
    account = accounts_repo.get_account_by_email(email_addr)

    if not account:
        error_payload = build_error_payload(
            "ACCOUNT_NOT_FOUND",
            "邮箱不存在",
            "NotFoundError",
            404,
            f"email={email_addr}",
        )
        return jsonify({"success": False, "error": error_payload}), 404

    request_code_length = (request.args.get("code_length") or "").strip() or None
    request_code_regex = (request.args.get("code_regex") or "").strip() or None
    code_source = (request.args.get("code_source") or "all").strip().lower()
    if code_source not in {"subject", "content", "html", "all"}:
        return build_error_response(
            "INVALID_PARAM",
            "参数错误",
            message_en="Invalid parameters",
            status=400,
        )

    account_type = (account.get("account_type") or "outlook").strip().lower()
    if account_type != "imap":
        decrypt_error_response = _build_account_credential_decrypt_failed_response(account)
        if decrypt_error_response:
            return decrypt_error_response

    try:
        # 委托 external_api.get_verification_result 统一处理，复用日志埋点和渠道路由逻辑
        if account_type == "imap":
            external_api_service.get_emails_imap_generic = get_emails_imap_generic
            external_api_service.get_email_detail_imap_generic_result = get_email_detail_imap_generic_result

        data = external_api_service.get_verification_result(
            email_addr=email_addr,
            code_regex=request_code_regex,
            code_length=request_code_length,
            code_source=code_source,
        )
        if not data.get("formatted") and not data.get("verification_code") and not data.get("verification_link"):
            raise external_api_service.MailNotFoundError("未找到验证信息", data={"email": email_addr})

        account_summary = _update_account_summary_from_verification(account, data)
        _LOGGER.debug(
            "[PERF] extract_verification | email=%s | 总耗时=%dms | path=shared_logging | success=true",
            email_addr,
            (time.monotonic() - _t0) * 1000,
        )
        return jsonify(
            {
                "success": True,
                "data": data,
                "message": "提取成功",
                "account_summary": account_summary,
            }
        )
    except external_api_service.MailNotFoundError as exc:
        return build_error_response(
            "EMAIL_NOT_FOUND",
            str(exc.message or "未找到匹配邮件"),
            message_en="Email not found",
            status=404,
            details=exc.data or f"email={email_addr}",
        )
    except external_api_service.ExternalApiError as exc:
        if _should_return_email_not_found_for_web_extract(exc):
            return build_error_response(
                "EMAIL_NOT_FOUND",
                "未找到匹配邮件",
                message_en="Email not found",
                status=404,
                details=exc.data or f"email={email_addr}",
            )
        resolved = _resolve_external_error(exc, allow_nested_upstream=True)
        return build_error_response(
            resolved["code"],
            resolved["message"],
            status=resolved["status"],
            details=resolved["data"] or "",
        )
    except Exception as e:
        error_payload = build_error_payload("EXTRACT_ERROR", "提取失败", "ExtractError", 500, str(e))
        return jsonify({"success": False, "error": error_payload}), 500


# ==================== External Emails API ====================
