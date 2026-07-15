# External API command center implementation

## Checklist

- Add `#externalApiCommandCenter` mount at the top of Settings -> API Security.
- Add a small settings snapshot and `renderExternalApiCommandCenter()` helpers in `static/js/main.js`.
- Call the renderer from `/api/settings` success, `/api/providers` success, and `/api/providers` failure paths.
- Add a secret-safe starter command copy action.
- Add CSS for compact metrics, endpoint rail, starter command, loading/unavailable states, and mobile stacking.
- Add i18n entries for new visible labels and copy feedback.
- Extend `tests/test_settings_tab_refactor_frontend.py` for the mount, JS hooks, CSS hooks, i18n, and no secret-value copy pattern.
- Run syntax checks, targeted settings/provider frontend tests, and browser desktop/mobile rendering checks.

## Validation Commands

```powershell
node --check static/js/main.js
node --check static/js/i18n.js
git diff --check
$env:PYTHONIOENCODING='utf-8'; python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_settings_external_api_key.py tests/test_multi_mailbox.py -q
```

Rendered check: log in with the test password, open Settings -> API Security, capture desktop and mobile screenshots, and assert `#externalApiCommandCenter` is ready with no horizontal overflow.

## Risk Notes

The main risk is accidentally implying that browser admin UI should call external endpoints with `X-API-Key`. Keep the command copy as a backend/client starter example with placeholder key only.

The second risk is duplicating provider routing rules in frontend code. The command center can display current source priority, active mode, and readiness counts, but must not reimplement provider selection logic.
