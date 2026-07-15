# Implementation Plan

1. In `loadMailboxProviderCatalog` success handler, after cache is set, call a small helper to refresh visible account provider tags from cache.
2. Helper: if `currentGroupId` and `accountsCache[currentGroupId]` exist, `renderAccountList` + optional `renderCompactAccountList`.
3. Contract test on main.js success path.
4. Validate.

## Validation

- Focused unittest
- `node --check static/js/main.js`
- `git diff --check`
