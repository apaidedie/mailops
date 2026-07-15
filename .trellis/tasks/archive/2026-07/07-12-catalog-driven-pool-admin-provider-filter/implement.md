# Implementation Plan

1. Clear hard-coded provider options in `templates/index.html` (keep empty “所有类型”).
2. Add `ensurePoolAdminProviderOptions()` in `static/js/features/pool_admin.js`.
3. Call it from `loadPoolAdmin()`.
4. Extend pool-admin frontend contract tests.

## Validation

- `python -m unittest tests.test_pool_admin_frontend_contract tests.test_pool_admin_ui_v2 -q`
- `node --check static/js/features/pool_admin.js`
- `git diff --check`
