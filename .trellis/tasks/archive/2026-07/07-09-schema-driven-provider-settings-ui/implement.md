# Implementation Plan

## Checklist

1. Remove DuckMail and Emailnator dedicated panels from `templates/index.html`.
2. Extend schema field normalization so catalog field keys map to their declared `settings_keys` when necessary.
3. Add generic schema-input hydration after settings and catalog loads.
4. Update schema collection to preserve unchanged non-secret defaults and blank secrets.
5. Simplify provider-change routing so only `legacy_bridge` and `cloudflare_temp_mail` use dedicated built-in panels, while plugin-backed providers continue through the plugin manager.
6. Update frontend contract tests to assert DuckMail/Emailnator are schema-driven rather than template panels.
7. Run focused syntax and test validation.

## Validation Commands

- `node --check static/js/main.js`
- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q`
- `python -m pytest tests/test_temp_mail_provider_public.py -q -k "settings_api_masks_key_and_preserves_placeholder or duckmail_settings_api_masks_token_and_preserves_placeholder or tempmail_lol_settings_api_masks_key_and_preserves_placeholder"`
- `python scripts/project_readiness_check.py --format json`
- `git diff --check`

## Risk Points

- Secret fields: blank input must preserve existing secret values.
- DuckMail API Base: unchanged env/default value must not be written into DB.
- JSON fields: invalid JSON must block save with a useful toast.
- Catalog load ordering: schema panel must hydrate correctly whether settings or provider catalog arrives first.
