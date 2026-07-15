# Unified mailbox provider capability UI

## Goal

Expose the backend provider capability matrix inside the unified mailbox workspace so operators can see which mailbox sources support each workflow, which selector field to send, and which providers still need configuration without opening external API documentation.

## User Value

The project is already usable at the backend/API level, but the unified mailbox page should make provider readiness visible enough for day-to-day use. The UI should help an operator answer: which providers are enabled, which workflows they support, how to route pool/task temp-mail calls, and whether configuration is missing.

## Confirmed Facts

- `templates/index.html` already contains `#unifiedProviderCapabilityMatrix` after provider context and before the mailbox list.
- `static/js/features/mailboxes.js` already renders a provider matrix, binds provider-row filtering, and receives `data.provider_context` from `/api/mailboxes`.
- Backend responses now expose `provider_context.readiness_summary.capability_matrix` with `providers`, `workflows`, `totals`, per-provider `workflow_support`, `selection_fields`, `configuration`, `read`, `lifecycle_actions`, and `endpoints`.
- Existing frontend tests assert the mount point, renderer names, provider filter binding, secret-safety constraints, and responsive CSS hooks.

## Requirements

- Prefer `provider_context.readiness_summary.capability_matrix` as the source of truth for the unified provider capability panel.
- Keep `provider_context.provider_integration_guide.providers` as a compatibility fallback only when the matrix is missing or empty.
- Render provider rows from data, not provider-name branches.
- Show workflow support, selector field/value hints, read actions, lifecycle actions, configuration state, and endpoint hints where present.
- Do not render provider secret values, Settings credential inputs, copied secret snippets, or provider-specific credential branches.
- Preserve the existing provider filter interaction: clicking a provider row updates `#unifiedMailboxProviderFilter` and reloads the mailbox directory.
- Keep the panel dense, responsive, and consistent with the existing Flask template + static JS/CSS frontend.

## Acceptance Criteria

- [ ] The matrix renderer consumes `readiness_summary.capability_matrix.providers` and `workflows` before falling back to guide providers.
- [ ] Provider rows display workflow support and selector fields from `workflow_support` / `selection_fields` without hardcoded provider names.
- [ ] Provider rows display configuration status from `configuration.needs_config` / `configuration.missing_config_count` and safe key names only.
- [ ] Provider rows display read actions, lifecycle actions, and endpoint hints from the matrix when present.
- [ ] Frontend contract tests cover the new matrix source, fallback behavior, CSS hooks, and secret-safety constraints.
- [ ] Focused frontend tests and whitespace checks pass.

## Out Of Scope

- No backend schema changes.
- No new provider integrations.
- No new frontend build system or framework.
- No remote push.
