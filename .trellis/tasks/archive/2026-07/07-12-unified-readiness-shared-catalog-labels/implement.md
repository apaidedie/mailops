# Implementation Plan

1. Broaden `getUnifiedMailboxProviderDisplayLabel` fallbacks to include `label`.
2. Wire readiness/routing/capability render paths.
3. Update unified mailbox frontend contract tests.
4. Validate.

## Validation

- Focused unittest
- `node --check static/js/features/mailboxes.js`
- `git diff --check`
