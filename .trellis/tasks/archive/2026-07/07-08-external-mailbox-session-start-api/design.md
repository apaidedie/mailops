# External mailbox session start API design

## Boundary

This task adds a thin orchestration endpoint for external callers. It must not create a second mailbox-reading implementation or a new lifecycle state machine. Existing services remain authoritative:

- Pool lifecycle: `outlook_web.services.pool.claim_random`, release, and complete endpoints.
- Task temp-mail lifecycle: `TempMailService.apply_task_mailbox` and finish endpoint.
- Read lifecycle: `get_external_mailbox_read_contract()` and existing external read endpoints.

## Endpoint

`POST /api/external/mailbox-sessions/start`

Request fields:

- `caller_id` and `task_id` are required.
- `source_strategy` defaults to `pool_first`; allowed values are `pool_first`, `task_temp_first`, `pool_only`, `task_temp_only`.
- `provider` selects pool claim provider.
- `provider_name` selects task temp-mail provider. If omitted and `provider` is present, task-temp fallback may use `provider` as the temp provider selector.
- `email_domain` and `project_key` pass through to pool claim.
- `prefix` and `domain` pass through to task temp-mail creation.

## Response Contract

The response envelope `data` is a `MailboxSessionData` object:

- Common fields: `session_type`, `email`, `provider`, `provider_label`, `read_capability`, `created_at`, `lifecycle`, `external_mailbox_read_contract`, `next_actions`.
- Pool fields under `lifecycle`: `account_id`, `claim_token`, `claimed_at`, `lease_expires_at`, `complete_endpoint`, `release_endpoint`.
- Task temp-mail fields under `lifecycle`: `task_token`, `finish_endpoint`, `visible_in_ui`, `status`.

The action contract remains the generated external mailbox read contract for the chosen lifecycle. The response may include `claim_token` and `task_token` because those are caller-held lifecycle handles required by existing APIs. It must not include stored mailbox credentials or provider secret values.

## Strategy Rules

- `pool_first`: try pool, then task temp-mail only when the pool is disabled or empty.
- `task_temp_first`: try task temp-mail first; if it fails due to no configured provider or upstream/provider issues, return that error. It may use pool only when task temp-mail is unavailable due to unsupported provider selection is not attempted in this first version. This keeps behavior predictable.
- `pool_only`: try pool only.
- `task_temp_only`: try task temp-mail only.

Fallback must not hide validation, authorization, scope, provider config, upstream, or internal errors.

## Permissions

Pool access remains gated by existing external pool permission semantics. Legacy API keys can use all strategies. Multi-key callers without `pool_access` can use `task_temp_only` only; strategies that include pool return `403 FORBIDDEN` before mutating state.

## Discovery and OpenAPI

The endpoint must be added to the shared external endpoint map so capabilities, provider guide, integration manifest, quickstart, readiness/OpenAPI, and generated clients agree on the path. OpenAPI gets a closed `MailboxSessionStartRequest` schema and typed `MailboxSessionData` response.

## Rollback

Revert route/controller additions, provider catalog endpoint/workflow additions, OpenAPI schemas/path, tests, and spec updates. No migration or persistent session records are introduced.
