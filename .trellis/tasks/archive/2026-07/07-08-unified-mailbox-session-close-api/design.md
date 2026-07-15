# Unified Mailbox Session Close API Design

## Architecture

Add a provider-neutral close endpoint beside session start:

```text
POST /api/external/mailbox-sessions/close
  -> validate external API key and public-mode feature guards
  -> parse close request
  -> route by session_type
      pool_claim + result=release -> pool.release_claim(...)
      pool_claim + valid completion result -> pool.complete_claim(...)
      task_temp_mailbox -> TempMailService.finish_task_mailbox(...)
  -> return normalized MailboxSessionCloseData
```

This endpoint is an orchestration adapter. It must call existing service functions rather than updating database rows directly.

## Request Contract

Common fields:

- `session_type`: `pool_claim` or `task_temp_mailbox`
- `caller_id`: caller identifier used at session start
- `task_id`: task identifier used at session start
- `result`: close result. For pool claims, `release` means release; other values must be existing pool completion results. For task temp-mail, this is an optional audit label.
- `detail`: optional audit detail

Pool fields:

- `account_id`
- `claim_token`
- `reason`: optional release reason, used only for `result=release`

Task temp-mail fields:

- `task_token`

## Response Contract

`MailboxSessionCloseData` is secret-free:

- `session_type`
- `close_action`: `complete_claim`, `release_claim`, or `finish_task_mailbox`
- `status`: `closed`
- Pool fields: `account_id`, `pool_status`
- Task fields: `task_token`, `email`

No response may include mailbox passwords, refresh tokens, provider JWTs, bearer tokens, API keys, consumer keys, or provider secret values.

## Discovery Updates

- Add `mailbox_session_close` to external endpoint maps.
- Add `close_endpoint` and `close_fields` to `mailbox_session` discovery.
- Add a `close_session` step after read in `integration_manifest.workflows.start_mailbox_session`.
- Add quickstart request example for `mailbox_session_close`.
- Add OpenAPI path, `MailboxSessionCloseRequest`, and `MailboxSessionCloseData` schemas.

## Compatibility

Specialized endpoints remain unchanged. Existing clients can continue using pool claim complete/release and task temp finish. New clients can use the unified close endpoint exclusively.

## Error Handling

Reuse external API envelopes and existing service errors. Invalid request shape returns `INVALID_PARAM`; missing handles return existing handle-specific codes where practical; service-level `PoolServiceError` and `TempMailError` map to their existing codes/statuses.

## Rollback

Remove the route, controller handler, discovery/OpenAPI/docs additions, and tests. Existing lifecycle endpoints are unchanged, so rollback does not require data migration.
