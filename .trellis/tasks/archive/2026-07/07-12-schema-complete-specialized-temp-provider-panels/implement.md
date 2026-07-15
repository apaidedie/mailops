# Implementation Plan

1. Expand `_TEMP_PROVIDER_CONFIG_CONTRACTS` for `legacy_bridge`, `custom_domain_temp_mail`, and `cloudflare_temp_mail` with full `config_schema.fields` and settings key lists.
2. Extend `settings_ui` projection with optional `actions`; set bridge/CF panels to generic schema mode.
3. Frontend schema renderer: support `readonly`, action buttons, and CF sync result mapping.
4. Route bridge/CF through schema panel only; stop dedicated panel show/hide for field editing.
5. Simplify `collectTempMailSettingsPayload` / `loadSettings` to schema-driven value transfer.
6. Remove or neutralize static specialized field markup in `templates/index.html` while preserving mount points if tests require.
7. Update multi-mailbox and settings frontend contract tests; run readiness + browser QA.

## Validation

- `python -m unittest tests.test_multi_mailbox tests.test_settings_tab_refactor_frontend -q`
- `node --check static/js/main.js`
- `python scripts/project_readiness_check.py`
- `git diff --check`
- Browser screenshots at 1440x1000 and 390x844 for Settings → Temp Mail bridge/CF/schema providers

## Rollback

- Keep CF sync endpoint and setting keys unchanged.
- Do not change provider runtime adapters.
