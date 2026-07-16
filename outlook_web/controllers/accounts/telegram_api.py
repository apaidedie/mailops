from __future__ import annotations

import copy
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from flask import Response, g, jsonify, request

from outlook_web import config
from outlook_web.audit import log_audit
from outlook_web.db import get_db
from outlook_web.errors import (
    build_error_payload,
    build_error_response,
    build_export_verify_failure_response,
)
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import groups as groups_repo
from outlook_web.repositories import refresh_logs as refresh_logs_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.repositories import tags as tags_repo
from outlook_web.repositories.distributed_locks import (
    acquire_distributed_lock,
    release_distributed_lock,
)
from outlook_web.repositories.refresh_runs import create_refresh_run, finish_refresh_run
from outlook_web.security.auth import get_client_ip, get_user_agent, login_required
from outlook_web.security.crypto import decrypt_data
from outlook_web.services import graph as graph_service
from outlook_web.services import refresh as refresh_service


@login_required
def api_telegram_toggle(account_id: int) -> Any:
    """切换账号通知参与开关。兼容旧 Telegram 专用接口路径。"""
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled", False))
    success = accounts_repo.toggle_telegram_push(account_id, enabled)
    if not success:
        error_payload = build_error_payload(
            "ACCOUNT_NOT_FOUND",
            "账号不存在",
            "NotFoundError",
            404,
            f"account_id={account_id}",
            message_en="Account not found",
        )
        return jsonify({"success": False, "error": error_payload}), 404
    action = "开启" if enabled else "关闭"
    log_audit(f"telegram_push_{action}", "account", str(account_id))
    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "notification_enabled": enabled,
            "message": f"该邮箱通知参与已{action}",
            "message_en": f"Mailbox notifications {'enabled' if enabled else 'disabled'}",
        }
    )


# ==================== 指定账号批量刷新 Token ====================
