from __future__ import annotations

from typing import Callable, Optional

from flask import Blueprint

from outlook_web.controllers import external_temp_emails as external_temp_emails_controller
from outlook_web.routes.external_api_aliases import add_external_api_url_rule


def create_blueprint(csrf_exempt: Optional[Callable] = None) -> Blueprint:
    bp = Blueprint("external_temp_emails", __name__)
    handlers = [
        (
            "/api/v1/external/mailboxes",
            external_temp_emails_controller.api_external_list_mailboxes,
            ["GET"],
        ),
        (
            "/api/v1/external/providers",
            external_temp_emails_controller.api_external_get_providers,
            ["GET"],
        ),
        (
            "/api/v1/external/providers/preflight",
            external_temp_emails_controller.api_external_get_provider_preflight,
            ["GET"],
        ),
        (
            "/api/v1/external/providers/<kind>/<provider>/health",
            external_temp_emails_controller.api_external_get_provider_health,
            ["GET"],
        ),
        (
            "/api/v1/external/mailbox-sessions/start",
            external_temp_emails_controller.api_external_start_mailbox_session,
            ["POST"],
        ),
        (
            "/api/v1/external/mailbox-sessions/read",
            external_temp_emails_controller.api_external_read_mailbox_session,
            ["POST"],
        ),
        (
            "/api/v1/external/mailbox-sessions/close",
            external_temp_emails_controller.api_external_close_mailbox_session,
            ["POST"],
        ),
        (
            "/api/v1/external/temp-emails/apply",
            external_temp_emails_controller.api_external_apply_temp_email,
            ["POST"],
        ),
        (
            "/api/v1/external/temp-emails/<task_token>/finish",
            external_temp_emails_controller.api_external_finish_temp_email,
            ["POST"],
        ),
    ]

    for path, handler, methods in handlers:
        add_external_api_url_rule(bp, path, view_func=handler, methods=methods, csrf_exempt=csrf_exempt)
    return bp
