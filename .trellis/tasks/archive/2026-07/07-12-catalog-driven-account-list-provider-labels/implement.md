# Implementation Plan

1. Replace hard-coded map in `groups.js`.
2. Trigger soft catalog load when cache empty during label resolution.
3. Add frontend contract assertions.
4. Validate.

## Validation

- Focused unittest on groups.js contract
- `node --check static/js/features/groups.js`
- `git diff --check`
- Optional browser screenshot of mailbox account cards if accounts exist
