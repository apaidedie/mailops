# Unified mailbox command center polish design

## Current Surface

The unified mailbox directory starts from `templates/index.html` and renders the command center through `static/js/features/mailboxes.js`. It already consumes `/api/mailboxes` for summary, facets, provider context, contract metadata, and quick-view presets. Styling lives in `static/css/main.css` under the `.unified-command-*` family.

## Design Direction

Keep the command center as an operational control surface, not a marketing hero. The first viewport should answer four practical questions: what inventory is available, which provider routing policy is active, where external callers should start, and which quick views are useful right now.

Use compact bands and stable grid areas. The visual hierarchy should make the inventory and routing state more prominent than decorative copy. Avoid nested cards and avoid one-off provider-specific UI.

## Data Contract

- Inventory and pagination: `data.summary` and `data.pagination`.
- Provider readiness and routing: `data.provider_context.provider_diagnostics.summary`, `data.provider_context.provider_filter`, `data.provider_context.defaults`, and `data.provider_context.selection_policy`.
- External entry point: `data.provider_context.provider_integration_guide.endpoints.mailboxes`, with discovery fallback only to documented endpoint paths.
- Quick views and filters: `data.contract.quick_view_presets`, `data.contract.*_definitions`, and `data.facets`.

The frontend may normalize field names for display but must not introduce provider-specific routing tables, secret value handling, or Settings credential reads.

## Implementation Shape

- Audit the current command-center render helper, supporting helpers, template mount order, CSS hooks, translations, and tests.
- If gaps are found, adjust helpers in `static/js/features/mailboxes.js` rather than adding separate render paths.
- Keep existing class naming and responsive breakpoints where possible; add CSS hooks only for real layout or wrapping needs.
- Update `static/js/i18n.js` only for user-facing copy that the UI uses.
- Extend `tests/test_unified_mailbox_frontend_contract.py` for structural and secret-safety checks.

## Validation

- Focused frontend contract tests for unified mailbox UI.
- Backend catalog regression tests if any payload assumptions are touched.
- JavaScript syntax checks for changed scripts.
- Secret scan for provider tokens and API keys.
- `git diff --check`.
- Browser QA on desktop and mobile with page-level overflow and key child-width checks.
