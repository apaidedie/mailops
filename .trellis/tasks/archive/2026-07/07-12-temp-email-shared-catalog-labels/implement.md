# Implementation Plan

1. Update `getTempEmailProviderDisplayLabel` in `static/js/features/temp_emails.js` to use `resolveMailboxProviderLabel` with temp-catalog/select fallbacks.
2. Add or extend frontend contract assertions.
3. Validate with focused unittest + `node --check` + `git diff --check`.

## Validation

- Focused unittest covering temp email label helper usage
- `node --check static/js/features/temp_emails.js`
- `git diff --check`
