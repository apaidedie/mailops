# Design

## Boundary

This task changes only the starter clients, their tests, and quickstart docs. The backend integration bundle remains the source of truth for action-plan semantics.

## Data Flow

`GET /api/v1/external/integration-bundle` -> client `integration_bundle()` / `integrationBundle()` -> `summarize_*_action_plan()` helper -> CLI `integration-bundle --summary` output.

For older deployments where the live bundle endpoint returns 404, 405, or 501, the clients already call capabilities, providers, and OpenAPI to assemble a compatibility bundle. The new summary helper must handle missing `action_plan` by deriving a conservative summary from fallback readiness fields without inventing provider-specific remediation.

## Contract

The summary projection is intentionally smaller than the backend action plan:

- `status`: bundle or action-plan status, defaulting to `unknown`.
- `summary`: total/blocking/high/medium/low counters from the plan when present.
- `blocking_keys`: item keys where `blocking=true`.
- `action_required_keys`: item keys where `status=action_required` or `status=blocked`.
- `ready_next_steps`: ready non-blocking item keys.
- `items`: ordered item summaries with `key`, `priority`, `status`, `blocking`, `title`, and optional safe target fields.

The helper may include placeholder commands and endpoint paths because the backend contract already requires those to be secret-safe. It must never add API key values or provider credential values from client configuration.

## CLI Shape

`integration-bundle` keeps the current JSON behavior by default. A new `--summary` flag prints the action-plan summary JSON to stdout or the requested `--output` path.

Using JSON for summary keeps scripts stable and avoids inventing a second human-only text parser.

## Compatibility

- No change to existing command names or existing `--output` behavior.
- No new runtime dependencies.
- No server calls beyond the existing integration-bundle/discovery calls.

## Rollback

Revert the starter-client helper and CLI flag changes plus their tests/docs. Existing backend API behavior is unaffected.
