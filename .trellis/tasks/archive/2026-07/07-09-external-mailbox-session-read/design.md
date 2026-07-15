# External Mailbox Session Read Endpoint Design

## Boundary

This task adds a session-level adapter, not a second mailbox reading system. Runtime mailbox reads remain owned by `outlook_web.services.external_api` and `outlook_web.services.mailbox_resolver`.

## Endpoint

`POST /api/external/mailbox-sessions/read`

Request body fields:

- `session_type`: required, `pool_claim` or `task_temp_mailbox`.
- `read_action`: required. Supported values: `messages`, `latest_message`, `message_detail`, `message_raw`, `verification_code`, `verification_link`, `wait_message`.
- `caller_id`: required for workflow continuity and audit context.
- `task_id`: required for workflow continuity and audit context.
- Pool lifecycle: `claim_token` required. `email` may be present but must match the token-resolved mailbox if supplied.
- Task temp lifecycle: `task_token` required. The controller resolves the task mailbox, verifies ownership against the current API consumer, and uses the resolved email for reads.
- Common read filters: `folder`, `skip`, `top`, `from_contains`, `subject_contains`, `since_minutes`.
- Action-specific fields: `message_id`, `code_length`, `code_regex`, `code_source`, `timeout_seconds`, `poll_interval`, `mode`.

## Data Flow

1. Route registers the endpoint in `outlook_web/routes/external_temp_emails.py`.
2. Controller validates JSON object body and session/read enums.
3. Controller resolves the session target:
   - `pool_claim`: call `external_api.resolve_external_mail_scope(email, claim_token)` to reuse claim-token validation, email consistency checks, access checks, and baseline timestamp.
   - `task_temp_mailbox`: call `temp_mail_service.get_task_mailbox(task_token)`, verify `consumer_key`, then call `external_api.resolve_external_mail_scope(email, None)` so the existing mailbox resolver checks active/finished status and access.
4. Controller dispatches `read_action` to existing service functions:
   - `messages`: `list_messages_for_external()` then `filter_messages()`.
   - `latest_message`: `get_latest_message_for_external()`.
   - `message_detail`: `get_message_detail_for_external()`.
   - `message_raw`: detail read plus raw-content projection.
   - `verification_code` / `verification_link`: `get_verification_result()` with the existing expected field.
   - `wait_message`: `create_probe()` for `mode=async`, otherwise `wait_for_message()`.
5. Controller returns the same response data shape as the existing direct read endpoint for that action, with the existing external API envelope.

## Compatibility

Existing direct read endpoints remain stable. Discovery should prefer the session read endpoint in the mailbox-session workflow, while `external_mailbox_read_contract.read_endpoints` keeps direct endpoints for legacy clients and advanced use.

## Discovery And OpenAPI

Add `MAILBOX_SESSION_READ_ENDPOINT` and expose it in:

- Provider catalog endpoint map.
- `get_external_mailbox_read_contract(lifecycle=pool_claim|task_temp_mailbox).next_actions` as `read_session`.
- Capabilities `features`, `endpoints`, and `mailbox_session` discovery object.
- Integration manifest quickstart and `start_mailbox_session` workflow.
- OpenAPI path and schemas: `MailboxSessionReadRequest` and `MailboxSessionReadData`.

`MailboxSessionReadData` is a wrapper with `session_type`, `read_action`, `email`, and `result` because each read action has its own result schema. The runtime envelope remains `external_api.ok(data)`.

## Security

The endpoint must not echo API keys, provider credentials, mailbox credentials, refresh tokens, provider bearer tokens, provider JWTs, consumer keys, or provider secret values. `claim_token` and `task_token` are caller-held lifecycle handles; the request consumes them, but the read response should not echo them.

Pool reads require `claim_token`. Task temp reads require `task_token` and current-consumer ownership. No provider-name conditionals are allowed.

## Rollback

The change is additive. Rollback is removing the new route, discovery entries, docs, tests, and controller helper paths. Existing endpoints are unchanged.
