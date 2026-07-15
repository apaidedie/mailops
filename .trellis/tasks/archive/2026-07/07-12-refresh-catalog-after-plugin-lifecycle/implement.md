# Implementation Plan

1. Add a small helper in `plugins.js` that force-refreshes catalog when `loadMailboxProviderCatalog` exists.
2. Call it after successful `loadPlugins` and `applyChanges` (install/uninstall already re-enter `loadPlugins`).
3. Extend frontend contract tests.
4. Validate.

## Validation

- Focused unittest
- `node --check static/js/features/plugins.js`
- `git diff --check`
