# Unified Mailbox Console UX Design

## Boundary

This task is a frontend-only enhancement over the current unified mailbox directory payload. It touches:

- `templates/index.html`
- `static/js/features/mailboxes.js`
- `static/css/main.css`
- `static/js/i18n.js`
- `tests/test_unified_mailbox_frontend_contract.py`

It does not change Flask routes, service contracts, provider catalog logic, OpenAPI output, or mailbox lifecycle behavior.

## UI Brief

- Audience: developers and operators managing mixed Outlook, IMAP, pool, and temp-mail provider inventory.
- Primary workflow: understand whether the current mailbox view is usable, why it may be empty or degraded, and what action to take next.
- Product archetype: operational SaaS console, dense and calm rather than marketing-style.
- Constraints: existing Flask templates, vanilla JS modules, CSS tokens in `main.css`, Chinese/English i18n, mobile responsiveness, no new UI framework.
- States: loading, error, empty, warning, ready, hover/focus, mobile collapse.
- Acceptance: contract tests plus focused browser/render checks when feasible.

## Data Flow

`/api/mailboxes` response -> `loadUnifiedMailboxes()` -> existing render pipeline -> new `renderUnifiedOperationalLens(data, state)`.

The lens consumes only the same response object already used by the page:

- `summary.total`, `summary.account`, `summary.temp`, status summary values
- `pagination.total_count`, `pagination.total_pages`, `filters`
- `facets.providers`, `facets.actions`, `facets.read_capabilities`
- `provider_context.provider_diagnostics.summary`
- `provider_context.readiness_summary.totals` and `issues`
- `contract.quick_view_presets`, `contract.action_definitions`

## Component Shape

`#unifiedMailboxOperationalLens` renders a three-column responsive surface:

- Current view: total/filtered count, active filter count, empty-state detail.
- Provider readiness: ready/active/needs-config counts and generic issue summary.
- Recommended action: one or two generic action buttons, such as refresh, clear to all mailboxes, switch to needs-attention quick view, or inspect provider context.

The render helper must not add inline `onclick` for provider filters. It may use `data-unified-lens-action` plus event delegation in `bindUnifiedMailboxControls()`.

## Safety And Compatibility

- Provider-specific behavior stays in backend/provider contracts. Frontend logic only reads normalized counts and labels.
- Secret-bearing input IDs and provider credential settings must not appear in the lens helper slice.
- Existing quick-view logic remains the source of truth for applying recommended preset actions.
- The lens is additive; if it fails to render, existing command center, filters, provider context, and mailbox cards still render.

## Responsive Layout

Desktop uses `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))` for lens cards. Mobile collapses naturally to one column and wraps action buttons. Long endpoint/action text uses `overflow-wrap: anywhere`.

## Rollback

Revert the template hook, JS render helpers/event delegation, CSS block, i18n entries, and test assertions. No data migration or backend rollback is required.
