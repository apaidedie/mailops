# Implementation Plan

## Steps

1. Add failing frontend/API contract tests for quickstart cache, helper fallback, cockpit rendering, copy action, i18n, CSS, and secret-safety.
2. Add the quickstart cache and helper functions in `static/js/main.js`.
3. Render the quickstart cockpit in `renderExternalApiCommandCenter()` and wire the copy button.
4. Add restrained responsive CSS in `static/css/main.css` and translations in `static/js/i18n.js`.
5. Run focused tests and syntax checks, then do diff and secret scans.

## Validation Commands

```powershell
python -m pytest tests/test_settings_tab_refactor_frontend.py -q -rs
python -m py_compile mailops\controllers\accounts.py mailops\services\provider_catalog.py
git diff --check
git diff | Select-String -Pattern 'dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN=|Bearer\s+[A-Za-z0-9_.-]+' -CaseSensitive:$false
```

## Rollback

Remove the quickstart cache/helper, cockpit rendering, copy handler, CSS, i18n entries, and tests. Existing external API command center behavior remains intact.
