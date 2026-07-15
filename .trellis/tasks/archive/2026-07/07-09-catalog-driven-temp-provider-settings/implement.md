# Catalog driven temp provider settings implementation plan

## Checklist

1. Read frontend quality specs for Settings provider UI, save payload reuse, and provider selectors.
2. Replace the hardcoded provider radio labels in `templates/index.html` with a stable dynamic mount and fallback loading shell.
3. Add catalog-driven provider option helpers in `static/js/main.js`:
   - fallback provider metadata.
   - normalize/catalog filter helpers.
   - option renderer.
   - selected/pending provider restoration.
   - catalog success/failure render hooks.
4. Keep `onTempMailProviderChange(provider)` as the panel router but simplify repeated show/hide operations where safe.
5. Update frontend contract tests in `tests/test_settings_tab_refactor_frontend.py` or add focused tests if a narrower file is clearer.
6. Run focused tests and syntax checks.
7. Run rendered Settings -> Temp Mail desktop/mobile QA if changed markup affects layout materially.
8. Run project readiness check and `git diff --check`.
9. Update `.trellis/spec/` if the implementation establishes a durable convention not already covered.
10. Commit, archive the Trellis task, and record the session journal.

## Validation Commands

```powershell
python -m pytest tests\test_settings_tab_refactor_frontend.py tests\test_settings_dynamic_provider_names.py -q
node --check static\js\main.js
node --check static\js\i18n.js
python scripts\project_readiness_check.py
git diff --check
```

## Rollback Point

- If catalog-driven rendering destabilizes Settings loading, revert only the dynamic mount, main.js selector helpers, and related tests. Keep existing provider backend/catalog work untouched.
