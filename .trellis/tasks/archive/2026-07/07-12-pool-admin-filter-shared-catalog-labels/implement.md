# Implementation Plan

1. Update `normalizePoolAdminProviderOptions` to use `resolveMailboxProviderLabel` / `getMailboxProviderCatalogLabel` when present.
2. Call `ensurePoolAdminProviderOptions(true)` from catalog load success path.
3. Update contract tests.
4. Validate.

## Validation

- Focused unittest
- `node --check` on touched files
- `git diff --check`
