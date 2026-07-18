# Implementation plan

## Steps

1. Add backend service `mailops/services/external_api_contract_check.py`.
2. Add settings controller and route for `/api/settings/external-api/contract-check`.
3. Add backend tests for auth, schema, pass/fail mapping, local-only posture, and secret safety.
4. Add frontend state/fetch/render helpers in `static/js/main.js`.
5. Insert the panel into `renderExternalApiCommandCenter()` after `renderExternalApiSmokeCheckPanel()`.
6. Add CSS for `.external-api-contract-check*` using existing command-center tokens.
7. Add i18n strings for visible labels.
8. Update frontend contract tests for helper names, endpoint usage, render order, CSS hooks, and secret-safety slices.
9. Run focused validation and browser QA.
10. Update specs if the new contract should be preserved for future sessions, then commit and archive task.

## Validation Commands

- `python -m pytest tests/test_module_boundaries.py tests/test_settings_tab_refactor_backend.py tests/test_settings_tab_refactor_frontend.py tests/test_external_api_smoke_script.py tests/test_external_api.py`
- `python scripts/project_readiness_check.py`
- `git diff --check`
- Browser QA against the running local app: Settings -> API Security command center, desktop and mobile overflow checks.

## Risk Points

- Importing `scripts.external_api_smoke` from a service is acceptable only if the script remains import-safe and no CLI execution side effects occur.
- The service must pass local envelope-shaped payloads to validation without making HTTP requests.
- Frontend validation helpers must not reference Settings credential input IDs or provider-specific names.
- Static contract tests are broad and may need targeted updates if render order assertions change.
