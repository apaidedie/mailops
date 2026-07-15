# External Mailbox Session Read Endpoint Implementation Plan

## Checklist

1. Add controller constants and helpers in `outlook_web/controllers/external_temp_emails.py` for session-read body parsing, target resolution, read parameter normalization, and action dispatch.
2. Register `POST /api/external/mailbox-sessions/read` in `outlook_web/routes/external_temp_emails.py`.
3. Update `outlook_web/services/provider_catalog.py` endpoint constants, read contracts, capabilities, quickstart, and integration manifest workflow to surface the session read action.
4. Update `outlook_web/services/external_api_openapi.py` schemas and paths for `MailboxSessionReadRequest` and `MailboxSessionReadData`.
5. Update `docs/external-integration-quickstart.md` to prefer start -> session read -> close.
6. Add focused tests to `tests/test_external_mailbox_session_start_api.py` for pool read, task temp read, task temp ownership rejection, discovery/OpenAPI exposure, and invalid input.
7. Update backend provider-selection spec if the new endpoint becomes part of the public external API contract.

## Validation Commands

- `python -m pytest tests/test_external_mailbox_session_start_api.py -q`
- `python -m pytest tests/test_external_temp_emails_api.py -q`
- `python -m pytest tests/test_external_api_smoke_script.py -q`
- `python -m py_compile outlook_web/controllers/external_temp_emails.py outlook_web/routes/external_temp_emails.py outlook_web/services/provider_catalog.py outlook_web/services/external_api_openapi.py`
- `git diff --check`

## Risk Points

- Do not duplicate mailbox resolver or provider read logic.
- Do not leak task mailbox `consumer_key` in audit or response payloads.
- Do not let task temp-mailbox reads bypass ownership checks.
- Keep OpenAPI and runtime discovery endpoint maps in sync.
- Preserve public-mode guards for raw content and wait-message behavior.
