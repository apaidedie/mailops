# External mailbox session start API

## Goal

External callers should be able to start a mailbox-reading session through one provider-neutral endpoint instead of choosing between the pool claim workflow and the task temp-mail workflow by hand. This moves the project closer to a professional unified mailbox aggregation service with a low-friction API surface for other services.

## Background

The project already exposes separate external APIs for provider discovery, unified mailbox directory browsing, pool claim lifecycle, task temp-mail creation/finish, message reads, verification extraction, async probes, and OpenAPI. The remaining integration friction is that callers must understand two lifecycle models before they can obtain a readable mailbox. A session start endpoint can wrap the existing lifecycle choices while preserving the existing read and finish/release APIs.

## Requirements

- Add `POST /api/external/mailbox-sessions/start` behind the existing external API key and guard chain.
- Accept a JSON object with `caller_id`, `task_id`, optional `source_strategy`, `provider`, `provider_name`, `email_domain`, `project_key`, `prefix`, and `domain`.
- Support `source_strategy` values: `pool_first`, `task_temp_first`, `pool_only`, and `task_temp_only`; default to `pool_first`.
- For pool-backed sessions, reuse the existing pool claim service and return the existing pool lifecycle identifiers and action contract.
- For task-temp-backed sessions, reuse the existing task temp-mail service and return the existing task token and action contract.
- In fallback modes, fall back only from an empty pool result (`no_available_account`) or disabled external pool, not from validation, authorization, provider configuration, upstream, or internal errors.
- Preserve current pool permission semantics: multi-key consumers without `pool_access` must not use `pool_first`, `task_temp_first`, or `pool_only` to silently bypass restricted pool access; they may use `task_temp_only`.
- Surface the endpoint through capabilities, provider guide endpoint maps, integration manifest workflows, quickstart endpoint maps, and OpenAPI.
- Keep response and discovery payloads secret-free. Do not expose API keys, provider bearer token values, passwords, refresh tokens, task tokens except the task mailbox token intentionally required to finish that task session, or provider secret values.

## Acceptance Criteria

- A successful `pool_first` request claims a pool mailbox when one is available and returns `session_type=pool_claim`, `email`, provider metadata, `claim_token`, `account_id`, lifecycle data, and an action contract with read and complete/release actions.
- A `pool_first` request falls back to task temp-mail creation when the pool has no available mailbox, returning `session_type=task_temp_mailbox`, `email`, provider metadata, `task_token`, lifecycle data, and an action contract with read and finish actions.
- A `task_temp_only` request succeeds for a multi-key API consumer without pool access and does not call pool claim.
- A multi-key API consumer without pool access receives `403 FORBIDDEN` for default `pool_first`, `task_temp_first`, and `pool_only` requests.
- Non-object JSON bodies and invalid `source_strategy` values return `400 INVALID_PARAM` before mutating pool or temp-mail state.
- Capabilities, provider catalog/manifest quickstart/workflows, and OpenAPI expose the new endpoint and typed request/response schemas.
- Focused external API tests pass, touched Python files compile, `git diff --check` passes, and the diff contains no real secret values.

## Out Of Scope

- Changing message retrieval, verification extraction, async probe behavior, pool completion/release semantics, or task temp-mail finish semantics.
- Adding a new database table for sessions; the endpoint returns existing lifecycle identifiers instead.
- UI work for this task.
