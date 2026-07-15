# External API Smoke UI Discoverability Implementation Plan

## Steps

1. Add frontend contract tests for smoke helper names, render placement, copy hook, secret safety, and CSS hooks.
2. Implement smoke command helpers in `static/js/main.js` without reading Settings credential inputs.
3. Render the smoke-check panel inside `renderExternalApiCommandCenter()`.
4. Add copy event handling and user feedback.
5. Add CSS for the smoke panel, coverage chips, command block, and mobile wrapping.
6. Update frontend spec documentation.
7. Run targeted frontend contract tests and relevant smoke/API tests.
8. Perform rendered desktop/mobile QA if a local server is available.

## Validation Commands

- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q`
- `python -m pytest tests/test_external_api_smoke_script.py -q`
- `python -m pytest tests/test_smoke_contract.py -q`

## Risk Notes

The main risk is accidentally reading or copying real API keys. Keep smoke helpers pure and placeholder-based, and cover the helper slice with forbidden-string tests.
