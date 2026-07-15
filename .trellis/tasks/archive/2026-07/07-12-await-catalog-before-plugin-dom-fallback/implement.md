# Implementation Plan

1. Make `_refreshMailboxProviderCatalogFromPlugins` async and await `loadMailboxProviderCatalog(true)`.
2. In `loadPlugins`, await catalog refresh then call `_refreshProviderRadios` / `_refreshProviderSelect`.
3. Drop redundant second catalog refresh in `applyChanges` (loadPlugins already handles it).
4. Update contract tests for await + reinjection markers.
5. Validate.

## Validation

- Focused unittest
- `node --check static/js/features/plugins.js`
- `git diff --check`
