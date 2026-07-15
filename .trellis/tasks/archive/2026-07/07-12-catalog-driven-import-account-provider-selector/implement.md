# Implementation Plan

1. Pass `note` through account catalog items in `provider_catalog.py`.
2. Update modal mount placeholder.
3. Harden `loadProviders` + note display in `accounts.js`.
4. Add frontend contract tests.

## Validation

- `python -m unittest tests.test_domain_provider_map tests.test_multi_mailbox.MultiMailboxSupportTests.test_builtin_temp_provider_settings_ui_contract -q` (or focused catalog test)
- New/updated frontend contract test for accounts import selector
- `node --check static/js/features/accounts.js`
- `git diff --check`
