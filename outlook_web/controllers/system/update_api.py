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
    get_external_api_readiness_summary,
    get_external_mailbox_read_contract,
    temp_mail_provider_label,
)
from outlook_web.services.scheduler import REFRESH_LOCK_NAME

from . import constants as _system_constants
from .helpers import _trigger_docker_api_update, _trigger_watchtower_update, _version_gt


@login_required
def api_version_check() -> Any:
    """检查是否有新版本可用（内存缓存，10 分钟 TTL；可通过 enable_version_check 关闭自动检查）"""
    import json as _json
    import urllib.request

    # 支持通过 settings 完全关闭版本检查
    if settings_repo.get_setting("enable_version_check", "true").lower() != "true":
        return jsonify(
            {
                "success": True,
                "has_update": False,
                "current_version": APP_VERSION,
                "latest_version": APP_VERSION,
                "release_url": "",
                "disabled": True,
            }
        )

    now = time.time()
    if (
        _system_constants._version_cache is not None
        and (now - _system_constants._version_cache_at) < _system_constants._VERSION_CACHE_TTL
    ):
        return jsonify(_system_constants._version_cache)

    current = APP_VERSION

    try:
        GITHUB_API = "https://api.github.com/repos/ZeroPointSix/outlookEmailPlus/releases/latest"
        req = urllib.request.Request(
            GITHUB_API,
            headers={"User-Agent": "outlook-email-plus"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read())
        latest = data.get("tag_name", "").lstrip("v")
        release_url = data.get("html_url", "")
        has_update = _version_gt(latest, current)
        result = {
            "success": True,
            "has_update": has_update,
            "current_version": current,
            "latest_version": latest,
            "release_url": release_url,
        }
    except Exception:
        # GitHub API 调用失败：静默降级，返回无更新
        result = {
            "success": True,
            "has_update": False,
            "current_version": current,
            "latest_version": current,
            "release_url": "",
        }

    _system_constants._version_cache = result
    _system_constants._version_cache_at = now
    return jsonify(result)


@login_required
def api_trigger_update() -> Any:
    """触发容器更新

    支持两种更新方式（通过 request 参数 method 指定）：
    1. watchtower (默认): 调用 Watchtower HTTP API
    2. docker_api: 使用 Docker API 自更新

    优先从数据库读取配置,如未配置则回退到环境变量。

    请求参数：
        method: str (可选) - 更新方式 (watchtower / docker_api)
        remove_old: bool (可选) - Docker API 模式下是否删除旧容器 (默认 False)
    """
    # 获取更新方式参数
    update_method = request.args.get("method", "watchtower").lower()

    if update_method == "watchtower":
        return _trigger_watchtower_update()
    elif update_method == "docker_api":
        return _trigger_docker_api_update()
    else:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"不支持的更新方式: {update_method} (支持: watchtower / docker_api)",
                }
            ),
            400,
        )


@login_required
def api_deployment_info() -> Any:  # noqa: C901
    """获取当前容器的部署信息（用于一键更新功能提示）

    检测内容：
    - 镜像名称和标签
    - 是否为本地构建（检查镜像名中是否包含 'local' / 'dev' / 没有 registry 前缀）
    - 是否使用固定版本标签（非 latest）
    - Watchtower 连通性

    返回示例：
    {
        "success": true,
        "deployment": {
            "image": "guangshanshui/outlook-email-plus:latest",
            "is_local_build": false,
            "uses_fixed_tag": false,
            "update_method": "watchtower",
            "watchtower_reachable": true,
            "can_auto_update": true,
            "warnings": []
        }
    }
    """
    import os

    # 当前选择的更新方式（用于生成更符合语境的提示）
    update_method = settings_repo.get_setting("update_method", "watchtower")
    if update_method not in ("watchtower", "docker_api"):
        update_method = "watchtower"

    deployment_info = {
        "image": "unknown",
        "is_local_build": False,
        "uses_fixed_tag": False,
        "update_method": update_method,
        "watchtower_reachable": None,
        "docker_api_available": False,
        "can_auto_update": False,
        "warnings": [],
    }

    # 1. 检测镜像信息
    # 优先策略（展示用途）：
    # - 只要 docker.sock 可用，就优先通过 Docker API 获取真实镜像名（不依赖 DOCKER_SELF_UPDATE_ALLOW）
    # - 否则回退到环境变量 DOCKER_IMAGE（可选）
    # - 再回退到 cgroup 近似判断
    image_name = os.getenv("DOCKER_IMAGE", "").strip()
    docker_image_id = ""
    docker_image_repo_digests: list[str] = []

    # 尝试通过 Docker API 获取镜像名（更准确；仅用于展示/提示）
    try:
        from outlook_web.services import docker_update

        socket_ok, _ = docker_update.check_docker_socket()
        if socket_ok:
            cinfo = docker_update.get_current_container_info()
            if cinfo:
                if cinfo.get("image"):
                    image_name = str(cinfo.get("image") or "").strip() or image_name
                docker_image_id = str(cinfo.get("image_id") or "").strip()
                repo_digests_raw = cinfo.get("image_repo_digests") or []
                if isinstance(repo_digests_raw, list):
                    docker_image_repo_digests = [str(x) for x in repo_digests_raw if str(x).strip()]
    except Exception:
        pass

    # 如果没有 DOCKER_IMAGE 环境变量，尝试读取 /proc/self/cgroup（仅 Linux）
    if not image_name:
        try:
            with open("/proc/self/cgroup", "r") as f:
                cgroup_content = f.read()
                # 简单判断：如果包含 docker 关键字，说明在容器内运行
                if "docker" in cgroup_content.lower() or "containerd" in cgroup_content.lower():
                    # 无法直接从 cgroup 读取镜像名，使用默认值
                    image_name = "outlook-email-plus:unknown"
        except Exception:
            pass

    # 2. 判断是否为本地构建
    # 注意：此前用 substring 检测 "test" 会误判 "latest"（包含 "test" 子串）。
    # 这里改为：优先用 Docker API 的 RepoDigests 判断（更可靠），并对 tag 做精确判断。
    def _parse_tag(ref: str) -> str:
        ref = (ref or "").strip()
        if not ref:
            return ""
        # digest 形式：repo@sha256:...
        if "@" in ref:
            ref = ref.split("@", 1)[0]
        # tag 形式：repo:tag（仅当最后一个 ':' 之后不包含 '/' 才视为 tag）
        if ":" in ref:
            left, right = ref.rsplit(":", 1)
            if "/" not in right:
                return right
        return ""

    is_local = False
    if image_name:
        deployment_info["image"] = image_name

        # 2.1 若能拿到 RepoDigests：为空通常表示本地 build（或未从 registry pull）
        if docker_image_id and isinstance(docker_image_repo_digests, list):
            if len(docker_image_repo_digests) == 0:
                is_local = True

        # 2.2 兜底：基于镜像名结构判断
        # 无 namespace（如 outlook-email-plus:latest）通常是本地构建或非官方镜像
        if not is_local:
            lower_image = image_name.lower()
            if "/" not in image_name or lower_image.startswith("outlook-email"):
                is_local = True
            else:
                tag = _parse_tag(image_name).lower()
                # 仅对 tag 做精确判断，避免 latest 被误判
                if tag in ("dev", "local", "test") or tag.startswith("dev-") or tag.startswith("local-"):
                    is_local = True

    deployment_info["is_local_build"] = is_local

    # 3. 判断是否使用固定标签
    # 策略：仅当 tag 符合语义化版本（如 v1.2.3、1.2.3）时才视为固定版本。
    # 分支名（如 hotupdate-test）、latest、main 等均视为滚动标签。
    import re

    uses_fixed_tag = False
    tag = _parse_tag(image_name)
    if tag:
        _semver_pattern = re.compile(r"^v?\d+\.\d+(\.\d+)?([._-].*)?$")
        if _semver_pattern.match(tag):
            uses_fixed_tag = True

    deployment_info["uses_fixed_tag"] = uses_fixed_tag

    # 4. 检测 Watchtower 连通性（使用已有配置）
    from outlook_web.security.crypto import decrypt_data, is_encrypted

    wt_url_raw = settings_repo.get_setting("watchtower_url", "")
    wt_token_raw = settings_repo.get_setting("watchtower_token", "")

    watchtower_url = wt_url_raw.strip() if wt_url_raw else os.getenv("WATCHTOWER_API_URL", "http://watchtower:8080")
    watchtower_token = ""
    if wt_token_raw:
        watchtower_token = decrypt_data(wt_token_raw) if is_encrypted(wt_token_raw) else wt_token_raw
    if not watchtower_token:
        watchtower_token = os.getenv("WATCHTOWER_HTTP_API_TOKEN", "")

    watchtower_reachable = False
    # 探测策略：发不带 token 的请求，401 = 服务可达（watchtower 在运行，只是未认证）。
    # 带 token 的请求会触发实际更新（拉镜像），耗时较长，不适合用作探测。
    if watchtower_url:
        try:
            import urllib.error
            import urllib.request

            probe_req = urllib.request.Request(
                f"{watchtower_url}/v1/update",
                method="GET",
            )
            with urllib.request.urlopen(probe_req, timeout=3) as resp:
                watchtower_reachable = resp.status == 200
        except urllib.error.HTTPError as e:
            # 401 Unauthorized = 服务可达，只是未提供 token
            watchtower_reachable = e.code == 401
        except Exception:
            watchtower_reachable = False

    deployment_info["watchtower_reachable"] = watchtower_reachable

    # 5. 检测 Docker API 可用性
    docker_api_available = False
    try:
        from outlook_web.services import docker_update

        if docker_update.is_docker_api_enabled():
            socket_ok, _ = docker_update.check_docker_socket()
            docker_api_available = socket_ok
    except Exception:
        docker_api_available = False

    deployment_info["docker_api_available"] = docker_api_available

    # 6. 生成警告信息
    warnings = []

    if is_local:
        warnings.append(
            {
                "type": "local_build",
                "severity": "warning",
                "message": "当前为本地构建模式，一键更新将无法工作",
                "message_en": "Local build detected. Auto-update is not available",
                "suggestion": "请使用远程镜像部署（如 guangshanshui/outlook-email-plus:latest）以支持一键更新",
                "suggestion_en": (
                    "Please use remote image (e.g., guangshanshui/outlook-email-plus:latest) for auto-update support"
                ),
            }
        )

    if uses_fixed_tag and not is_local:
        warnings.append(
            {
                "type": "fixed_tag",
                "severity": "info",
                "message": "当前使用固定版本标签，一键更新需手动修改 docker-compose.yml 中的版本号",
                "message_en": "Fixed version tag detected. Auto-update requires manual tag change in docker-compose.yml",
                "suggestion": "建议使用 latest 标签以支持自动更新",
                "suggestion_en": "Consider using 'latest' tag for auto-update support",
            }
        )

    # 智能推荐更新方式：根据实际可用性决定
    # 优先级：用户已保存的偏好 > 自动检测
    if update_method == "watchtower" and not watchtower_reachable and docker_api_available:
        recommended_method = "docker_api"
    elif update_method == "docker_api" and not docker_api_available and watchtower_reachable:
        recommended_method = "watchtower"
    else:
        recommended_method = update_method
    deployment_info["recommended_method"] = recommended_method

    # Watchtower 连通性提示：根据推荐方式决定严重级别
    if not watchtower_reachable and not is_local:
        if recommended_method == "watchtower":
            warnings.append(
                {
                    "type": "watchtower_unreachable",
                    "severity": "error",
                    "message": "无法连接 Watchtower 服务",
                    "message_en": "Cannot connect to Watchtower service",
                    "suggestion": "请确保 Watchtower 容器正常运行，并在系统设置中配置正确的 API 地址和 Token",
                    "suggestion_en": (
                        "Please ensure Watchtower container is running and API credentials are configured correctly"
                    ),
                }
            )
        # Docker API 可用时不再显示 Watchtower 不可达提示（避免噪音）

    # Docker API 可用性提示
    if recommended_method == "docker_api" and not is_local:
        if not docker_api_available:
            warnings.append(
                {
                    "type": "docker_api_unavailable",
                    "severity": "error",
                    "message": "Docker API 更新方式不可用（未挂载 docker.sock 或权限不足）",
                    "message_en": "Docker API update is unavailable (docker.sock not mounted or insufficient permissions)",
                    "suggestion": "请在部署时挂载 /var/run/docker.sock 并设置 DOCKER_SELF_UPDATE_ALLOW=true",
                    "suggestion_en": "Mount /var/run/docker.sock and set DOCKER_SELF_UPDATE_ALLOW=true",
                }
            )

    deployment_info["warnings"] = warnings

    # 7. 判断是否可以使用一键更新
    can_auto_update = not is_local and (watchtower_reachable or docker_api_available)

    deployment_info["can_auto_update"] = can_auto_update

    return jsonify({"success": True, "deployment": deployment_info})


@login_required
def api_test_watchtower() -> Any:  # noqa: C901
    """测试 Watchtower 连通性：用配置的 URL + Token 请求 /v1/update (HEAD)"""
    import os
    import urllib.error
    import urllib.request

    from outlook_web.security.crypto import decrypt_data, is_encrypted

    data = request.get_json(silent=True) or {}
    wt_url = str(data.get("url", "")).strip()
    wt_token = str(data.get("token", "")).strip()

    # 如果前端没传值，从数据库 / 环境变量读取
    if not wt_url:
        wt_url_raw = settings_repo.get_setting("watchtower_url", "")
        wt_url = wt_url_raw.strip() if wt_url_raw else os.getenv("WATCHTOWER_API_URL", "http://watchtower:8080")
    if not wt_token:
        wt_token_raw = settings_repo.get_setting("watchtower_token", "")
        if wt_token_raw:
            wt_token = decrypt_data(wt_token_raw) if is_encrypted(wt_token_raw) else wt_token_raw
        if not wt_token:
            wt_token = os.getenv("WATCHTOWER_HTTP_API_TOKEN", "")

    if not wt_url:
        return jsonify({"success": False, "message": "Watchtower URL 未配置"})

    # 先测试连通性（GET /v1/update 返回 200 表示 API 可达）
    # 注意: Watchtower 的 GET /v1/update 也会触发完整的镜像检查流程,
    # 包括从 GHCR 拉取 manifest, 可能需要 20-30 秒才能返回
    try:
        test_req = urllib.request.Request(
            f"{wt_url}/v1/update",
            method="GET",
            headers={
                "Authorization": f"Bearer {wt_token}",
            },
        )
        with urllib.request.urlopen(test_req, timeout=35):
            return jsonify(
                {
                    "success": True,
                    "message": f"Watchtower 连通正常 ({wt_url})",
                    "message_en": f"Watchtower is reachable at {wt_url}",
                }
            )
    except urllib.error.HTTPError as e:
        # 401 说明 API 可达但 Token 错误
        if e.code == 401:
            return jsonify(
                {
                    "success": False,
                    "message": "Watchtower 可达但认证失败，请检查 Token",
                    "message_en": "Watchtower is reachable but authentication failed. Check your token.",
                }
            )
        return jsonify(
            {
                "success": False,
                "message": f"Watchtower 返回状态码 {e.code}",
            }
        )
    except urllib.error.URLError as e:
        return jsonify(
            {
                "success": False,
                "message": f"无法连接 Watchtower ({wt_url}): {e.reason}",
                "message_en": f"Cannot connect to Watchtower ({wt_url}): {e.reason}",
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"测试失败: {str(e)}"})
