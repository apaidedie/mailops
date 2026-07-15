# Implementation Plan

1. Add `getUnifiedMailboxProviderDisplayLabel(mailbox)` helper in `mailboxes.js`.
2. Use it from card render and preview label helpers.
3. Update unified mailbox frontend contract tests.
4. Validate.

## Validation

- Focused unittest
- `node --check static/js/features/mailboxes.js`
- `git diff --check`
