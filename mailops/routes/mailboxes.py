from __future__ import annotations

from flask import Blueprint

from mailops.controllers import mailboxes as mailboxes_controller


def create_blueprint() -> Blueprint:
    bp = Blueprint("mailboxes", __name__)
    bp.add_url_rule("/api/mailboxes", view_func=mailboxes_controller.api_list_mailboxes, methods=["GET"])
    bp.add_url_rule(
        "/api/mailboxes/<kind>/<int:source_id>/messages",
        view_func=mailboxes_controller.api_list_mailbox_messages,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/mailboxes/<kind>/<int:source_id>/messages/<path:message_id>",
        view_func=mailboxes_controller.api_get_mailbox_message_detail,
        methods=["GET"],
    )
    bp.add_url_rule(
        "/api/mailboxes/<kind>/<int:source_id>/verification",
        view_func=mailboxes_controller.api_get_mailbox_verification,
        methods=["GET"],
    )
    return bp
