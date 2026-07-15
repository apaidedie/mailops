# Schema Driven Provider Settings Implementation Plan

## Checklist

1. Inspect focused code paths for Settings Temp Mail rendering, settings load/save, provider catalog configuration payloads, and existing plugin schema rendering.
2. Read `trellis-before-dev` and the backend/frontend specs before editing implementation files.
3. Add or expose sanitized built-in provider configuration metadata only if current catalog payloads are insufficient.
4. Add the generic provider configuration mount in `templates/index.html`.
5. Implement frontend metadata projection helpers in `static/js/main.js`:
   - resolve active temp provider metadata
   - build safe field definitions
   - render generic config panel states
   - collect generic config values with secret-preserve semantics
6. Keep Cloudflare Worker, legacy bridge, and plugin-provider special flows compatible while moving Mail.tm-compatible providers to the generic surface.
7. Add or adjust CSS for compact field grids, key-name wrapping, secret hints, and mobile collapse.
8. Update Settings frontend contract tests and any provider catalog tests affected by schema projection.
9. Run focused validation commands.
10. Run rendered desktop/mobile Settings checks because UI layout changes are expected.
11. Run Trellis finish checks, update specs if new durable rules were learned, commit, archive, and journal.

## Validation Commands

```powershell
node --check static\js\main.js
node --check static\js\features\plugins.js
python -m pytest tests\test_settings_tab_refactor_frontend.py tests\test_settings_dynamic_provider_names.py -q
python -m pytest tests\test_temp_mail_provider_public.py tests\test_temp_mail_target_contract.py -q
python scripts\project_readiness_check.py
git diff --check
```

If provider catalog contracts change, also run:

```powershell
python -m pytest tests\test_multi_mailbox.py tests\test_external_temp_emails_api.py -q
```

## Browser QA

- Start the Flask app with scheduler autostart disabled on an available localhost port.
- Open Settings -> Temp Mail at desktop `1440x1000` and mobile `390x844`.
- Verify provider selector, generic config panel, special panels, and plugin panel states.
- Inspect `document.documentElement.scrollWidth - clientWidth`, the Settings Temp Mail pane, and the generic provider panel for horizontal overflow.
- Save screenshots under ignored `output/playwright/` paths when useful.

## Risk Points

- Secret fields accidentally prefilled or serialized as placeholders.
- Tests asserting old dedicated panels too strongly.
- Provider routing regressions between settings UI and backend catalog naming.
- Mobile Settings wrappers with inline padding squeezing dense provider fields.
- Existing special flows losing event handlers during panel migration.
