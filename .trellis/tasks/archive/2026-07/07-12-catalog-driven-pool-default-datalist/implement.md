# Implementation Plan

1. Cache `selection_policy` from `/api/providers` in `loadMailboxProviderCatalog`.
2. Add `getPoolDefaultProviderAllowedValues()` + `renderPoolDefaultProviderDatalist()`.
3. Call renderer after successful catalog load (and safe no-op when mount missing).
4. Clear hard-coded `<option>` list in `templates/index.html`.
5. Update frontend contract tests.

## Validation

- `python -m unittest tests.test_settings_tab_refactor_frontend -q`
- `node --check static/js/main.js`
- `git diff --check`
