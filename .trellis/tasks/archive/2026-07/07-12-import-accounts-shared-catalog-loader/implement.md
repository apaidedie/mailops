# Implementation Plan

1. Update `loadProviders` in `accounts.js` to prefer shared cache + `loadMailboxProviderCatalog`.
2. Keep direct `/api/providers` and offline auto/outlook as fallbacks.
3. Update frontend contract tests.
4. Validate.

## Validation

- Focused unittest
- `node --check static/js/features/accounts.js`
- `git diff --check`
