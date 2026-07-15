# Implementation Plan

1. Add `getImportResultProviderLabel()` in `accounts.js`.
2. Replace hard-coded `provNames` usage in auto-import success toast.
3. Extend `tests/test_v190_frontend_contract.py` (or accounts contract) assertions.
4. Validate with focused unittest + node check + diff check.

## Validation

- `python -m unittest tests.test_v190_frontend_contract.V190FrontendContractTests.test_import_account_provider_selector_is_catalog_driven tests.test_v190_frontend_contract.V190FrontendContractTests.test_import_result_provider_labels_are_catalog_driven -q`
- `node --check static/js/features/accounts.js`
- `git diff --check`
