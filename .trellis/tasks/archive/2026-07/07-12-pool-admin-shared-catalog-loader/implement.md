# Implementation Plan

1. Update `ensurePoolAdminProviderOptions` to call shared catalog loader when cache is empty.
2. Keep direct fetch only as last-resort fallback.
3. Update frontend contract tests.
4. Validate.

## Validation

- Focused unittest
- `node --check static/js/features/pool_admin.js`
- `git diff --check`
