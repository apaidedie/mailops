# Design

## UI Brief

Audience: operators and external integrators managing mixed Outlook/IMAP accounts, temp-mail providers, and API-facing mailbox inventory.

Primary workflow: open the unified mailbox page, understand current inventory/provider readiness, filter to the needed mailbox source or capability, then open/copy a mailbox action.

Product archetype: operational SaaS and data-product workspace. Dense but calm, with restrained surfaces, strong scan path, and stable controls.

Constraints: Flask templates, static CSS/JavaScript, existing i18n helper, existing backend contract definitions, no new library, no provider-specific frontend registry, secret-free UI.

States: loading, error, empty, ready, hover, focus, active quick view, selected provider facet, mobile/tablet/desktop responsive states.

Acceptance: contract tests for template/JS/CSS hooks, focused catalog regression tests if contract assumptions are touched, rendered/browser check when feasible, diff whitespace check, secret-safety review.

## Boundaries

Implementation stays inside the unified mailbox workspace:

- `templates/index.html` for static shell classes and initial loading markup.
- `static/css/main.css` for layout, visual hierarchy, responsive behavior, and interaction states.
- `static/js/features/mailboxes.js` for rendered markup refinements using existing `/api/mailboxes` payload fields.
- `tests/test_unified_mailbox_frontend_contract.py` for contract hooks where structure/classes are intentionally added or refined.

Backend services/controllers are out of scope unless tests prove the frontend currently cannot consume the documented contract safely.

## Contract Consumption

The frontend continues to consume these backend-owned values:

- `data.summary`, `data.pagination`, and `data.facets` for counts and filters.
- `data.contract.*_definitions`, `summary_fields`, and `quick_view_presets` for labels and enum-driven controls.
- `data.provider_context` and `provider_context.readiness_summary` for provider policy/readiness/status bands.
- `item.action_contract.internal.open_mailbox` for opening records.
- `item.actions` and `contract.action_definitions` for action chips.

The UI must not rebuild provider selection priority, provider aliases, or provider capability rules in JavaScript.

## Visual Direction

Use a calm mission-control direction:

- Light operational surfaces, compact metrics, and restrained blue/green/orange semantic accents.
- Keep cards at 8px radius to match the project style.
- Use grid/flex constraints instead of viewport-scaled typography.
- Avoid decorative blobs, marketing hero structure, or nested card-heavy composition.
- Prefer visible focus rings and state color changes that do not move layout bounds.

## Responsive Design

Desktop keeps the command center as a two-column dashboard. Tablet collapses the main command panels and provider grids to fewer columns. Mobile forces all command-center children into the single-column flow with explicit `grid-column: 1 / -1` and `grid-row: auto`, while horizontal scrolling is limited to deliberate rails.

Filter controls collapse into two columns and then one column. Provider capability rows and mailbox cards collapse to a single column so long endpoints, provider names, and email addresses wrap instead of squeezing the layout.

## Compatibility And Rollback

The safest rollback is limited to the task files. Because backend APIs are not changed, rollback should restore the previous template/CSS/JS/test shapes without migration work.
