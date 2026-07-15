# Implementation Plan

1. Add failing catalog contract tests for `settings_ui`, aliases, panel modes, fields, and plugin extensibility.
2. Extend provider catalog configuration projection with normalized UI metadata.
3. Update settings/provider payload tests and secret-safety assertions.
4. Refactor `main.js` provider option and panel selection logic to consume `settings_ui` only.
5. Replace static template options with catalog-loading placeholders and update frontend contract tests/i18n as needed.
6. Run focused backend/frontend tests, readiness, format/lint/type checks, and `git diff --check`.
7. Start the app and verify Settings -> Temp Mail on desktop and mobile, including a generic provider and specialized panels.

## Validation

- `python -m unittest tests.test_provider_catalog tests.test_settings_api tests.test_frontend_contracts -v`
- `python scripts/project_readiness_check.py`
- `node --check static/js/main.js`
- project Black/isort/Flake8/mypy gates for changed Python modules
- browser screenshots and zero-overflow checks at 1440x1000 and 390x844

## Rollback Points

- Keep existing specialized panel DOM until catalog-driven routing is verified.
- Do not alter provider runtime selection or upstream adapters.
