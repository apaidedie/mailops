# Design

## Boundaries

- Frontend only: update `static/js/features/mailboxes.js`, `static/css/main.css`, and `tests/test_unified_mailbox_frontend_contract.py`.
- Data source: use `/api/mailboxes` response `provider_context.readiness_summary.capability_matrix` already produced by the backend.
- Compatibility: keep the existing `provider_integration_guide.providers` path as fallback for older payloads.

## Data Flow

1. `loadUnifiedMailboxes()` fetches `/api/mailboxes` and passes `data.provider_context` plus `unifiedMailboxState.contract` into `renderUnifiedProviderCapabilityMatrix()`.
2. The renderer calls a matrix normalizer that reads `providerContext.readiness_summary.capability_matrix`.
3. Provider rows are projected into a display model with provider key, kind, state, workflow support, selector fields, read actions, lifecycle actions, configuration metadata, inventory, and endpoints.
4. If the matrix is missing, the display model falls back to the existing guide-provider projection so older deployments still show a useful panel.
5. The renderer writes only escaped HTML and preserves the existing click-to-filter behavior through `.unified-provider-capability-filter`.

## UI Brief

- Audience: operators integrating mailbox providers and external services.
- Primary workflow: scan provider readiness and pick the right provider/selector for unified mailbox, pool, task temp-mail, and session flows.
- Product archetype: dense operational SaaS workspace.
- Constraints: Flask templates, static JavaScript, existing CSS tokens, no provider-specific JS behavior, secret-safe display.
- States: loading, empty, error, ready, active selected provider, responsive mobile collapse.
- Acceptance: focused contract tests plus whitespace checks; rendered browser check if the app can start cleanly in this environment.

## Rendering Contract

- Prefer `readiness_summary.capability_matrix.providers` when it is a non-empty array.
- Use `capability_matrix.workflows` to render workflow summary chips and labels.
- Use `providers[*].workflow_support` to mark workflow support per provider.
- Use `providers[*].selection_fields` to render selector field/value hints.
- Use `providers[*].configuration` only for status/counts/key names, not secret values.
- Use `providers[*].read.actions`, `providers[*].lifecycle_actions`, and `providers[*].endpoints` for capability details.

## Tradeoffs

- Keep the existing row-based panel instead of adding a separate workflow table. This avoids another mount point and preserves the current operational flow.
- Show endpoint hints as compact key/path pairs. Full API docs remain in the external integration guide.
- Keep fallback support in the same normalizer instead of a second renderer, so the UI has one code path and one interaction model.
