from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Response, jsonify, request

from outlook_web import __version__ as APP_VERSION
from outlook_web import config
from outlook_web.db import (
    DB_SCHEMA_LAST_UPGRADE_ERROR_KEY,
    DB_SCHEMA_LAST_UPGRADE_TRACE_ID_KEY,
    DB_SCHEMA_VERSION,
    DB_SCHEMA_VERSION_KEY,
    create_sqlite_connection,
)
from outlook_web.repositories import accounts as accounts_repo
from outlook_web.repositories import settings as settings_repo
from outlook_web.security.auth import api_key_required, get_external_api_consumer, login_required
from outlook_web.security.external_api_guard import external_api_guards
from outlook_web.services import external_api as external_api_service
from outlook_web.services import mailbox_resolver
from outlook_web.services.external_api_docs import render_external_api_docs_html
from outlook_web.services.external_api_openapi import get_external_api_openapi_contract
from outlook_web.services.provider_catalog import (
    get_external_api_capabilities_contract,
    get_external_api_integration_bundle,
    get_external_mailbox_read_contract,
    get_external_api_readiness_summary,
    temp_mail_provider_label,
)
from outlook_web.services.scheduler import REFRESH_LOCK_NAME

from .constants import _LOCAL_DEMO_DB_RELATIVE_PATH, _REPO_ROOT, logger

def _safe_demo_workspace_metadata() -> dict[str, Any]:
    """Return secret-safe metadata for the explicit local demo database."""
    database_path = Path(config.get_database_path())
    try:
        expanded = database_path.expanduser()
        configured = (expanded if expanded.is_absolute() else (Path.cwd() / expanded)).resolve(strict=False)
        expected = (_REPO_ROOT / _LOCAL_DEMO_DB_RELATIVE_PATH).resolve(strict=False)
        enabled = configured == expected
    except OSError:
        enabled = False

    if not enabled:
        return {"enabled": False}

    return {
        "enabled": True,
        "label": "Local demo workspace",
        "database": _LOCAL_DEMO_DB_RELATIVE_PATH.as_posix(),
        "synthetic": True,
        "quick_actions": [
            {"key": "overview", "label": "Overview", "page": "dashboard", "tab": "summary"},
            {"key": "unified_mailbox", "label": "Unified mailbox", "page": "mailbox"},
            {"key": "temp_mailboxes", "label": "Temp mailboxes", "page": "temp-emails"},
            {"key": "external_api", "label": "External API", "page": "dashboard", "tab": "external-api"},
            {"key": "providers", "label": "Provider settings", "page": "settings", "tab": "api-security"},
        ],
    }

def utcnow() -> datetime:
    """返回 naive UTC 时间（等价于旧的 datetime.utcnow()）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _version_gt(a: str, b: str) -> bool:
    """判断版本 a 是否严格大于版本 b（支持语义化版本 x.y.z，忽略 pre-release 后缀如 -hotupdate-test）"""
    try:

        def _parse(v: str) -> tuple:
            # 取 '-' 之前的纯数字部分，如 "1.12.1-hotupdate-test" → "1.12.1"
            core = v.split("-", 1)[0]
            return tuple(int(x) for x in core.split("."))

        return _parse(a) > _parse(b)
    except Exception:
        return False

def _trigger_watchtower_update() -> Any:  # noqa: C901
    """通过 Watchtower HTTP API 触发更新"""
    import os
    import urllib.error
    import urllib.request

    from outlook_web.security.crypto import decrypt_data, is_encrypted

    # 优先从数据库读取,回退到环境变量
    wt_url_raw = settings_repo.get_setting("watchtower_url", "")
    wt_token_raw = settings_repo.get_setting("watchtower_token", "")

    watchtower_url = wt_url_raw.strip() if wt_url_raw else os.getenv("WATCHTOWER_API_URL", "http://watchtower:8080")
    watchtower_token = ""
    if wt_token_raw:
        watchtower_token = decrypt_data(wt_token_raw) if is_encrypted(wt_token_raw) else wt_token_raw
    if not watchtower_token:
        watchtower_token = os.getenv("WATCHTOWER_HTTP_API_TOKEN", "")

    if not watchtower_token:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Watchtower Token 未配置,请在系统设置 → 一键更新中配置",
                }
            ),
            500,
        )

    try:
        req = urllib.request.Request(
            f"{watchtower_url}/v1/update",
            method="POST",
            headers={
                "Authorization": f"Bearer {watchtower_token}",
                "Content-Length": "0",
            },
            data=b"",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            resp_body = resp.read().decode("utf-8", errors="replace").strip()

        if status == 200:
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Watchtower 响应: status=%s body=%r", status, resp_body[:500])
            # Watchtower POST /v1/update 是同步的：完成整个检查+更新周期后才返回。
            # 如果我们的容器需要更新，Watchtower 会先停止旧容器再启动新容器，
            # 此时我们的进程已被 kill，HTTP 请求会失败而不会收到 200。
            # 因此：能收到 200 响应 → 本容器未被更新 → 镜像已是最新。
            return jsonify(
                {
                    "success": True,
                    "already_latest": True,
                    "message": "Watchtower 检查完毕，当前已是最新版本",
                    "message_en": "Watchtower check complete, already up to date",
                    "watchtower_response": resp_body[:500] if resp_body else None,
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Watchtower 返回状态码 {status}",
                        "detail": resp_body[:500] if resp_body else None,
                    }
                ),
                502,
            )
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace").strip()[:500]
        except Exception:
            pass
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Watchtower 返回错误 (HTTP {e.code})",
                    "detail": body or str(e.reason),
                }
            ),
            502,
        )
    except urllib.error.URLError as e:
        reason_str = str(e.reason) if e.reason else "未知原因"
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"无法连接 Watchtower ({watchtower_url})",
                    "detail": reason_str,
                }
            ),
            503,
        )
    except TimeoutError:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"连接 Watchtower 超时 ({watchtower_url})",
                    "detail": "请求在 30 秒内未收到响应，可能是网络问题或 Watchtower 拉取镜像耗时过长",
                }
            ),
            504,
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"触发更新失败: {type(e).__name__}: {str(e)}"}), 500

def _trigger_docker_api_update() -> Any:  # noqa: C901
    """通过 Docker API 触发容器自更新

    A2（按需 helper job 容器）模式：
    - 主应用容器只负责创建一个短生命周期 updater 容器
    - updater 容器执行真正的更新流程（并在适当时机 stop/rename 旧容器）
    - 主接口尽量快速返回，减少“响应中途被 stop”导致的失败概率
    """
    import json
    import os

    from flask import request, session

    from outlook_web.audit import log_audit
    from outlook_web.services import docker_update

    # 检查是否启用 Docker API 自更新
    if not docker_update.is_docker_api_enabled():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Docker API 自更新功能未启用 (需设置环境变量 DOCKER_SELF_UPDATE_ALLOW=true)",
                }
            ),
            403,
        )

    # 检查 docker.sock 可访问性
    socket_ok, socket_msg = docker_update.check_docker_socket()
    if not socket_ok:
        return (
            jsonify(
                {
                    "success": False,
                    "message": socket_msg,
                }
            ),
            503,
        )

    # 获取参数
    remove_old = request.args.get("remove_old", "false").lower() == "true"
    username = session.get("username", "unknown")

    # 先在主线程记录一次审计日志（后台线程没有 request context）
    try:
        log_audit(
            "trigger_docker_api_update_start",
            "system",
            "docker_update",
            json.dumps(
                {
                    "method": "docker_api",
                    "remove_old": remove_old,
                    "username": username,
                },
                ensure_ascii=False,
            ),
        )
    except Exception:
        # 审计日志失败不影响主流程
        pass

    # A2: 使用按需 updater 容器执行更新，避免“容器 stop 自己”导致流程中断。
    # 这里尽量快速返回，updater 会延迟几秒再开始 stop。
    try:
        # 当前容器 ID 通常等于 HOSTNAME（短 ID），但 docker SDK 接受短/长 ID
        target_id = os.getenv("HOSTNAME", "").strip()
        if not target_id:
            return jsonify({"success": False, "message": "无法获取当前容器 ID"}), 500

        # 安全：API 层也做镜像白名单/本地构建拦截（策略A），避免等到 spawn 内部才失败。
        try:
            cinfo = docker_update.get_container_info(target_id)
            if not cinfo:
                return (
                    jsonify({"success": False, "message": "无法获取目标容器信息"}),
                    500,
                )

            image_ref = str(cinfo.get("image") or "").strip()
            image_id = str(cinfo.get("image_id") or "").strip()
            ok_img, img_msg = docker_update.validate_image_for_update(
                image_ref,
                image_id=image_id,
            )
            if not ok_img:
                return jsonify({"success": False, "message": img_msg}), 403
        except Exception:
            # 校验异常：不放行（宁可阻止也不冒险更新到未知镜像）
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "镜像安全校验失败，已阻止更新请求（请检查部署镜像与 docker 权限）",
                    }
                ),
                500,
            )

        # Digest 预检查：先 pull 镜像并比较 digest，避免 updater 空跑导致前端等待超时
        try:
            pull_ok, pull_msg, new_digest = docker_update.pull_latest_image(image_ref)
            if pull_ok and new_digest:
                if docker_update.compare_image_digest(image_id, new_digest):
                    return jsonify(
                        {
                            "success": True,
                            "message": "当前已是最新版本，无需更新",
                            "already_latest": True,
                        }
                    )
        except Exception:
            # pull 失败不阻断：交给 updater 容器内部重试
            pass

        ok, msg = docker_update.spawn_update_helper_container(
            target_id,
            remove_old=remove_old,
            start_delay_seconds=2,
            auto_remove=True,
        )
        if not ok:
            return jsonify({"success": False, "message": msg}), 500
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        logger.error(f"启动 updater 容器失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"启动 updater 失败: {str(e)}"}), 500
