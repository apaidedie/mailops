# External integration workbench UI Implementation Plan

## Steps

1. Read frontend specs and existing command center helpers.
2. Add session lifecycle helper functions in `static/js/main.js` near quickstart/workflow helpers.
3. Insert the rendered lifecycle panel into `renderExternalApiCommandCenter` before the general endpoint/snippet grid.
4. Add copy wiring for the session lifecycle guide.
5. Add CSS for stable desktop/mobile panel layout.
6. Add or extend tests for JS helper names, copy wiring, endpoint surfacing, secret-safety, provider-agnostic behavior, CSS hooks, and i18n strings.
7. Run focused frontend/i18n tests, syntax checks, and whitespace checks.
8. Commit and archive the Trellis task if checks pass.

## Validation Commands

- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q`
- `python -m pytest tests/test_i18n_settings_completeness.py -q`
- `python -m pytest tests/test_ui_settings_external_api_key.py -q`
- `python -m py_compile mailops/controllers/external_temp_emails.py mailops/routes/external_temp_emails.py`
- `git diff --check`

## Risk Notes

- `static/js/main.js` tests use string slices around helper names, so helper placement must preserve existing slice boundaries.
- Keep new session workbench helpers before provider workbench functions so existing tests can inspect their secret-safe region.
- Avoid adding live `/api/external/*` calls from Settings UI; endpoints are display/copy material only.
