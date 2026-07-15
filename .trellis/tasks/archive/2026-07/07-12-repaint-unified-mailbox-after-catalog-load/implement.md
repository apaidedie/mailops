# Implementation Plan

1. Cache last `provider_context` / provider facets on unified mailbox state.
2. Add `refreshUnifiedMailboxProviderLabelsFromCatalog()` that re-renders list + context + capability matrix from cache.
3. Call it from catalog success in `main.js`.
4. Update frontend contract tests.
5. Validate.

## Validation

- Focused unittest
- `node --check` on touched JS
- `git diff --check`
