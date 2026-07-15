# Implementation Plan

1. Call `loadMailboxProviderCatalog(false)` from `DOMContentLoaded` after core init starts (non-blocking).
2. Assert boot call site in frontend contract tests.
3. Validate node check + focused tests + diff check.

## Validation

- Focused unittest for boot path
- `node --check static/js/main.js`
- `git diff --check`
