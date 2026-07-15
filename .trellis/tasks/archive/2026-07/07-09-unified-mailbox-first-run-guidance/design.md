# Unified mailbox first-run guidance design

## UI Brief

- Audience: operators and developers using the app as a combined Outlook/IMAP and temporary-mail aggregation service.
- Primary workflow: open the unified mailbox workspace, understand whether mailbox sources and external integration are ready, then take the next setup action.
- Product archetype: operational SaaS/data product, dense but calm.
- Constraints: Flask templates, vanilla JavaScript, existing CSS tokens, no new libraries, secret-safe frontend, provider-agnostic provider handling.
- Source of truth: existing unified mailbox DOM, `/api/mailboxes` payload, frontend quality specs, provider-selection contract.
- States: loading, empty inventory, partial provider readiness, ready, unknown/error.
- Acceptance: contract tests, JS syntax checks, readiness checker, rendered desktop/mobile overflow check.

## Boundaries

- Add a single setup guidance panel inside the existing unified mailbox layout.
- Reuse the current `/api/mailboxes` response. The renderer may consume `summary`, `provider_context`, `provider_context.readiness_summary`, `provider_context.documentation`, `provider_context.selection_policy`, and available external contract hints when present.
- Do not add backend fields unless current payload proves insufficient during implementation.
- Do not inspect Settings form fields, local storage secrets, or provider-specific environment variable names.

## Rendering Model

- Add a template mount point near the unified command center / operational lens so the guide is visible before the mailbox list.
- Add a small renderer that builds a normalized setup model from aggregate counts and metadata:
  - mailbox inventory readiness from summary counts.
  - provider readiness from readiness summary totals or capability matrix aggregates.
  - external integration readiness from documented external API paths or integration contract metadata when present.
  - validation readiness from existing documentation/check hints when present.
- Render three or four prioritized actions with status chips, a short title, compact detail, and a safe action link/button.
- Actions should point to existing in-app anchors or canonical docs/API routes; placeholders must not contain secrets.

## Styling Model

- Use un-nested cards only for repeated setup steps.
- Keep the panel as an unframed workspace band with a constrained inner grid.
- Use neutral surfaces, semantic status accents, compact typography, and stable min-height/spacing so loading and loaded states do not jump.
- Mobile collapses to a single column with touch-friendly buttons.

## Compatibility

- Existing quick views, filters, provider matrix, mailbox list, and pagination must keep working.
- Tests should assert provider-agnostic behavior by scanning for forbidden provider-name branches in the new helpers.
- Secret safety is enforced by tests looking for credential-field reads and secret-copy patterns.
