# Implementation Plan

1. Add `getMailboxProviderCatalogLabel` / `resolveMailboxProviderLabel` in main.js near catalog helpers.
2. Update groups.js and accounts.js consumers.
3. Update frontend contract tests.
4. Validate.

## Validation

- Focused unittest for main/groups/accounts contracts
- `node --check` on touched JS files
- `git diff --check`
