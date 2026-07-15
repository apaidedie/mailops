# Implementation Plan

## Steps

1. Read applicable frontend/backend/guides specs before editing.
2. Add failing frontend contract tests for the new workspace view control, default render order, JS state/helper/event binding, i18n labels, and CSS/mobile selectors.
3. Update `templates/index.html` to group unified mailbox content into inbox workflow and diagnostics sections while preserving existing IDs.
4. Update `static/js/features/mailboxes.js` with provider-agnostic view state, view switch helper, event binding, render-state reflection, and language rerender handling.
5. Update `static/css/main.css` with stable dense layout for the inbox workflow and diagnostics sections across desktop/mobile.
6. Update `static/js/i18n.js` for new labels.
7. Run focused tests and browser QA.

## Validation Commands

`python -m pytest tests/test_unified_mailbox_frontend_contract.py -q`

`python -m pytest tests/test_module_boundaries.py tests/test_unified_mailbox_catalog.py tests/test_unified_mailbox_frontend_contract.py -q`

`python scripts/project_readiness_check.py`

`git diff --check`

Browser QA: run the existing demo workspace flow and inspect desktop/mobile overflow for the default inbox workflow and diagnostics view.

## Rollback Points

If grouping the full page creates layout instability, keep the view switch and move only the provider diagnostics into the diagnostics section first. If JS view state creates regressions, fall back to CSS-only default ordering while preserving the new DOM group wrappers.
