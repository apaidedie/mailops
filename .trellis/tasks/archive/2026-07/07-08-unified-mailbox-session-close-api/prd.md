# Unified mailbox session close API

## Goal

Give external workers a provider-neutral way to close mailbox sessions after registration work. Today `/api/external/mailbox-sessions/start` hides whether the worker received a pool claim or a task-scoped temp mailbox, but lifecycle close-out still requires the worker to branch into `/api/external/pool/claim-complete`, `/api/external/pool/claim-release`, or `/api/external/temp-emails/{task_token}/finish`. This task adds a unified close endpoint so the shortest integration path becomes: discover -> start session -> read mail -> close session.

## User Value

- External services can integrate with one session lifecycle contract instead of coupling to pool and temp-mail internals.
- Future mailbox source types can add lifecycle adapters behind the same close API without changing external worker code.
- The project moves closer to a professional unified mailbox aggregation service with stable external contracts.

## Confirmed Facts

- `POST /api/external/mailbox-sessions/start` already returns `session_type`, `lifecycle`, `next_actions`, and read contracts.
- Pool sessions are currently closed through `/api/external/pool/claim-complete` or `/api/external/pool/claim-release`.
- Task temp-mail sessions are currently closed through `/api/external/temp-emails/{task_token}/finish`.
- OpenAPI and `integration_manifest.workflows.start_mailbox_session` currently document start/read but not a single provider-neutral close step.
- Existing guards, API-key auth, pool access checks, audit logging, request length constants, and lifecycle services should be reused.

## Requirements

1. Add `POST /api/external/mailbox-sessions/close` protected by the same external API key and guard chain as session start.
2. The close request must support `session_type=pool_claim` and `session_type=task_temp_mailbox`.
3. For `pool_claim`, the close endpoint must accept `account_id`, `claim_token`, `caller_id`, `task_id`, `result`, optional `detail`, and optional `reason`.
4. For `pool_claim`, `result=release` must release the claim; all other valid pool result values must complete the claim through the existing pool service.
5. For `task_temp_mailbox`, the close endpoint must accept `task_token`, `caller_id`, `task_id`, optional `result`, and optional `detail`, then finish the existing task temp mailbox through the existing temp-mail service.
6. The close endpoint must not create a third lifecycle model, mutate mailboxes directly, or duplicate pool/temp finish semantics beyond request routing and response normalization.
7. The close response must be a secret-free `MailboxSessionCloseData` object with `session_type`, `close_action`, `status`, and source-specific identifiers such as `account_id`, `pool_status`, `task_token`, and `email` when available.
8. Discovery payloads, integration manifest quickstart/workflows, OpenAPI schemas, and the external integration quickstart document must expose the unified close endpoint.
9. Existing specialized close endpoints must remain compatible for current clients.
10. Tests must cover success paths, invalid request handling, permission/ownership behavior, discovery/OpenAPI exposure, and secret-safety.

## Acceptance Criteria

- [ ] `POST /api/external/mailbox-sessions/close` closes a pool claim via completion when `session_type=pool_claim` and `result` is a valid pool completion result.
- [ ] The same endpoint releases a pool claim when `session_type=pool_claim` and `result=release`.
- [ ] The same endpoint finishes a task temp mailbox when `session_type=task_temp_mailbox`.
- [ ] Invalid JSON, missing/invalid `session_type`, invalid pool result, missing required lifecycle handles, and unauthorized task-token ownership return structured external API errors without mutating state.
- [ ] `/api/external/capabilities`, `/api/external/providers`, `integration_manifest`, and `/api/external/openapi.json` expose the close endpoint and typed request/response schemas.
- [ ] `docs/external-integration-quickstart.md` recommends the unified close endpoint while preserving references to specialized endpoints as compatibility options.
- [ ] Existing external API, pool, temp-mail, and session-start tests remain green.

## Out of Scope

- Removing or deprecating specialized pool/task close endpoints.
- Adding a persisted `sessions` database table.
- Changing mailbox read endpoints or verification extraction behavior.
- UI changes beyond any static contract text already generated from discovery payloads.
