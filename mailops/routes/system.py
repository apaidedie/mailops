from __future__ import annotations

from flask import Blueprint

from mailops.controllers import system as system_controller
from mailops.routes.external_api_aliases import add_external_api_url_rule
from mailops.security.auth import login_required


def create_blueprint() -> Blueprint:
    """创建 system Blueprint"""
    bp = Blueprint("system", __name__)
    bp.add_url_rule("/healthz", view_func=system_controller.healthz, methods=["GET"])
    bp.add_url_rule(
        "/api/bootstrap",
        view_func=system_controller.api_bootstrap,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/system/health",
        view_func=system_controller.api_system_health,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/system/diagnostics",
        view_func=system_controller.api_system_diagnostics,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/system/upgrade-status",
        view_func=system_controller.api_system_upgrade_status,
        methods=["GET"],
    )

    # PRD-00008 / FD-00008：对外开放系统自检接口（仅 API Key 鉴权）
    add_external_api_url_rule(
        bp,
        "/api/v1/external/health",
        view_func=system_controller.api_external_health,
        methods=["GET"],
    )
    add_external_api_url_rule(
        bp,
        "/api/v1/external/capabilities",
        view_func=system_controller.api_external_capabilities,
        methods=["GET"],
    )
    add_external_api_url_rule(
        bp,
        "/api/v1/external/integration-bundle",
        view_func=system_controller.api_external_integration_bundle,
        methods=["GET"],
    )
    add_external_api_url_rule(
        bp,
        "/api/v1/external/openapi.json",
        view_func=system_controller.api_external_openapi,
        methods=["GET"],
    )
    add_external_api_url_rule(
        bp,
        "/api/v1/external/docs",
        view_func=system_controller.api_external_docs,
        methods=["GET"],
    )
    add_external_api_url_rule(
        bp,
        "/api/v1/external/account-status",
        view_func=system_controller.api_external_account_status,
        methods=["GET"],
    )

    # FD: 版本更新检测与一键更新
    bp.add_url_rule(
        "/api/system/version-check",
        view_func=system_controller.api_version_check,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/system/trigger-update",
        view_func=system_controller.api_trigger_update,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/system/deployment-info",
        view_func=system_controller.api_deployment_info,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/system/test-watchtower",
        view_func=system_controller.api_test_watchtower,
        methods=["POST"],
    )

    @bp.post("/api/system/reload-plugins")
    @login_required
    def api_reload_plugins():
        return system_controller.api_reload_plugins()

    return bp
