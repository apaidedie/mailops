# Implementation plan

## Steps

1. Read the relevant Trellis frontend/backend/spec guides before editing.
2. Add pure renderer helpers in `static/js/main.js` for external API consumer summary, item normalization, tone selection, and HTML rendering.
3. Insert the consumer usage console into `renderExternalApiCommandCenter()` after the handoff kit and before aggregate command metrics.
4. Add responsive CSS in `static/css/main.css` for summary metrics and consumer cards using existing tokens and 8px radius.
5. Add focused frontend contract tests in `tests/test_settings_tab_refactor_frontend.py` for placement, safe-field policy, and expected rendering terms/classes.
6. Run syntax, tests, whitespace checks, and browser QA for desktop/mobile Settings -> API Security.
7. Update project spec if this creates a reusable UI/security convention, then commit and archive the task.

## Validation

- `node --check static/js/main.js`
- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q`
- `python -m pytest tests/test_settings_external_api_key.py tests/test_external_api.py -q`
- `git diff --check`
- Browser QA on desktop and mobile viewports for Settings -> API Security.

## Risk Points

- Accidentally rendering `api_key` or `api_key_masked` in the usage console.
- Introducing layout overflow in the already dense API Security tab.
- Breaking multi-key save behavior by reusing editor normalization incorrectly.
