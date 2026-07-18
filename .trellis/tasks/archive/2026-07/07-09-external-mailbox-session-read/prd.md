# External mailbox session read endpoint

## Goal

Make the external mailbox-session workflow complete for third-party callers by adding one provider-neutral session read endpoint after `POST /api/external/mailbox-sessions/start` and before `POST /api/external/mailbox-sessions/close`.

The endpoint should reduce client branching between pool claims and task temp-mailboxes while keeping the existing mailbox read implementation, authorization, claim-token baseline behavior, and provider resolver as the source of truth.

## Confirmed Facts

- `POST /api/external/mailbox-sessions/start` already returns `session_type`, `email`, lifecycle handles, `external_mailbox_read_contract`, and `next_actions` for `pool_claim` and `task_temp_mailbox` sessions.
- `POST /api/external/mailbox-sessions/close` already closes pool claims and task temp-mailboxes through existing lifecycle services.
- Existing read behavior lives on `/api/external/messages`, `/api/external/messages/latest`, `/api/external/messages/{message_id}`, `/api/external/messages/{message_id}/raw`, `/api/external/verification-code`, `/api/external/verification-link`, and `/api/external/wait-message`.
- `mailops.services.external_api.resolve_external_mail_scope()` already resolves `email` or `claim_token`, enforces mailbox access, and applies the pool claim baseline timestamp.
- `mailops.services.mailbox_resolver.ensure_mailbox_can_read()` already enforces account email scope and task temp-mailbox consumer ownership.
- Historical API docs explicitly avoid adding a separate task-token-specific message API. This task must not create a parallel task mailbox read subsystem.

## Requirements

- Add `POST /api/external/mailbox-sessions/read` as a provider-neutral session read endpoint protected by the existing API-key auth and external guard chain.
- Accept a JSON body with `session_type`, `read_action`, `caller_id`, `task_id`, and the lifecycle handle required by the session type: `claim_token` for `pool_claim`, or `task_token` for `task_temp_mailbox`.
- Support the common read actions needed by external workers: message list, latest message, message detail, raw message, verification code, verification link, and wait-message async/sync.
- Reuse existing external read service functions for mailbox resolution, authorization, filtering, verification extraction, wait/probe creation, and raw/detail reads.
- For pool sessions, prefer the existing `claim_token` scope so reads inherit claim ownership and claimed-at baseline filtering.
- For task temp-mailbox sessions, resolve the mailbox from `task_token`, verify the current external API consumer owns it, then read by resolved email through the existing temp-mail resolver path. The response must not echo provider secrets or consumer keys.
- Keep existing legacy read endpoints fully compatible.
- Expose the new endpoint through provider catalog discovery, capabilities, integration manifest workflows, quickstart data, OpenAPI, and external integration docs.
- Keep schemas and runtime responses secret-safe: no mailbox passwords, refresh tokens, provider bearer tokens, provider JWTs, API keys, consumer keys, or provider secret values.
- Keep implementation provider-agnostic. Do not branch on DuckMail, mail.tm, GPTMail, Emailnator, Outlook, or other provider names.

## Acceptance Criteria

- [ ] `POST /api/external/mailbox-sessions/read` returns a typed session-read wrapper whose `result` field preserves the same data shape as the underlying read action for `messages`, `latest_message`, `message_detail`, `message_raw`, `verification_code`, `verification_link`, and `wait_message`.
- [ ] Pool session reads work with `session_type=pool_claim` and `claim_token`, apply the existing claim baseline behavior, and record claim read audit context.
- [ ] Task temp-mailbox session reads work with `session_type=task_temp_mailbox` and `task_token` owned by the current external API consumer.
- [ ] Task temp-mailbox session reads with another consumer's `task_token` are rejected with a forbidden response.
- [ ] Invalid JSON, invalid `session_type`, invalid `read_action`, missing lifecycle handles, and unsupported raw-content/wait-message public-mode settings return existing structured error envelopes.
- [ ] `/api/external/capabilities`, `/api/external/providers`, `integration_manifest`, `quickstart`, and `GET /api/external/openapi.json` expose the new session read endpoint and typed request/response schemas.
- [ ] Documentation shows the preferred start -> read -> close flow using the session read endpoint, while noting that older direct read endpoints remain compatible.
- [ ] Focused tests and static checks pass before commit.

## Out Of Scope

- Persisting a new session table or changing mailbox lifecycle storage.
- Replacing the existing `/api/external/messages*`, verification, wait, or probe endpoints.
- Adding provider-specific read paths or provider-name conditionals.
- UI redesign work; this task is backend/API contract work that improves the external integration foundation.

## Notes

- This is a complex cross-layer API contract task. It requires `design.md` and `implement.md` before implementation.
