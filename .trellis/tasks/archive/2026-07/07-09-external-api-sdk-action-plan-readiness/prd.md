# External API SDK Action Plan Readiness

## Goal

Make the zero-dependency Python and JavaScript starter clients consume the integration bundle `action_plan` as an operator-facing readiness summary, so external services can quickly decide whether they may start mailbox sessions or must resolve blocking setup work first.

## Background

- The live integration bundle already exposes `data.action_plan` with prioritized, machine-readable remediation and next-action items.
- The current starter clients prefer the live bundle endpoint and can fall back to locally assembling an older-service bundle from capabilities, providers, and OpenAPI.
- The current `integration-bundle` CLI command prints or writes raw JSON only. That is correct for automation, but it does not surface blocking/action-required items in a concise way for humans or CI logs.
- Starter clients must stay dependency-free, read-only for discovery commands, and secret-safe.

## Requirements

- Add shared action-plan projection helpers in both starter clients without rebuilding backend provider-selection or readiness rules.
- The projection must accept live bundle `action_plan` objects and locally assembled fallback bundles.
- The projection must expose status, summary counters, blocking item keys, action-required item keys, ready next-step item keys, and a small ordered item list suitable for logs.
- The `integration-bundle` CLI command must support a summary mode that prints the concise action-plan projection instead of the full bundle JSON.
- The existing JSON and output-file behavior must remain backwards compatible.
- The summary output must not include real API keys, provider bearer tokens, passwords, JWTs, refresh tokens, consumer keys, claim tokens, task tokens, or provider secret values.

## Acceptance Criteria

- [x] Python starter client exports an action-plan summary helper and covers live bundle, fallback bundle, CLI summary output, and secret safety in tests.
- [x] JavaScript starter client exports equivalent action-plan summary behavior and covers live bundle, fallback bundle, CLI summary output, and secret safety in tests.
- [x] The summary mode uses only read-only discovery endpoints and does not call mailbox-session mutation endpoints.
- [x] Docs mention the summary mode near the starter client `integration-bundle` examples.
- [x] Targeted Python and JavaScript client tests pass.
- [x] Project readiness and diff whitespace checks pass.

## Out Of Scope

- Changing the backend `action_plan` schema or provider readiness calculation.
- Adding third-party SDK packaging, package publishing, or generated OpenAPI clients.
- Reworking the Settings UI action-plan renderer.
