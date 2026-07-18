from __future__ import annotations

from typing import Callable, Optional

from flask import Blueprint

from mailops.controllers import external_pool as external_pool_controller
from mailops.routes.external_api_aliases import add_external_api_url_rule


def create_blueprint(csrf_exempt: Optional[Callable] = None) -> Blueprint:
    """创建 external_pool Blueprint。

    外部池接口面向 worker/合作方直接调用，POST 请求不应被浏览器态 CSRF 校验拦截。
    这里统一在 Blueprint 装配阶段透传 csrf_exempt，避免后续新增端点时遗漏。
    """
    bp = Blueprint("external_pool", __name__)
    handlers = [
        (
            "/api/v1/external/pool/claim-random",
            external_pool_controller.api_external_pool_claim_random,
            ["POST"],
        ),
        (
            "/api/v1/external/pool/claim-release",
            external_pool_controller.api_external_pool_claim_release,
            ["POST"],
        ),
        (
            "/api/v1/external/pool/claim-complete",
            external_pool_controller.api_external_pool_claim_complete,
            ["POST"],
        ),
        (
            "/api/v1/external/pool/stats",
            external_pool_controller.api_external_pool_stats,
            ["GET"],
        ),
    ]

    # 所有 external_pool 端点都走同一套鉴权链路，这里只负责统一挂载 CSRF 豁免。
    for path, handler, methods in handlers:
        add_external_api_url_rule(bp, path, view_func=handler, methods=methods, csrf_exempt=csrf_exempt)
    return bp
