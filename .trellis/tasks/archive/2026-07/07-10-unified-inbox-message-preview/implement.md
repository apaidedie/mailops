# Implementation Plan

## Steps

Create backend service `unified_mailbox_messages.py` with mailbox resolution, message list normalization, detail normalization, verification normalization, and service-level `UnifiedMailboxMessageError`.

Add `get_temp_email_by_id` to the temp email repository for source-id resolution.

Add controller handlers and route registrations under `/api/mailboxes/<kind>/<source_id>/...`.

Update unified mailbox template with a preview panel mount point after the mailbox list/pagination area.

Update `static/js/features/mailboxes.js` with preview state, fetch loaders, renderers, event delegation, card button changes, verification copy, language rerender, and fallback navigation.

Update `static/css/main.css` with dense preview layout, selected card state, list/detail pane, loading/empty/error states, and mobile collapse.

Update i18n strings for new labels.

Add backend tests to `tests/test_unified_mailbox_catalog.py` or a focused new test file for admin unified message preview API.

Add frontend contract tests to `tests/test_unified_mailbox_frontend_contract.py`.

Run focused tests, module-boundary tests, readiness check, diff check, and browser QA for desktop/mobile overflow.

## Validation Commands

`python -m py_compile outlook_web/services/unified_mailbox_messages.py outlook_web/controllers/mailboxes.py outlook_web/routes/mailboxes.py outlook_web/repositories/temp_emails.py`

`python -m pytest tests/test_module_boundaries.py tests/test_unified_mailbox_catalog.py tests/test_unified_mailbox_frontend_contract.py -q`

`python scripts/project_readiness_check.py`

`git diff --check`

Browser QA should inspect desktop and mobile unified mailbox preview panel overflow.

## Rollback Points

If backend normalization conflicts with existing account/temp read paths, keep the route layer but reduce scope to list-only preview before detail. If visual QA shows layout instability, keep backend API and hide preview panel behind a compact collapsed state until fixed.
