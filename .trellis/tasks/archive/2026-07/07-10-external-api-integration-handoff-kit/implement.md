# Implementation Plan

## Checklist

1. Add normalized helper functions in `static/js/main.js` for handoff sections, action-plan text, selector text, session examples, docs links, and full copy text.
2. Add `renderExternalApiHandoffKit()` and `copyExternalApiHandoffKit()` and place the renderer after `renderExternalApiBundleLaunchpad(...)` in `renderExternalApiCommandCenter()`.
3. Add event delegation for `data-external-api-handoff-copy`.
4. Add CSS classes in `static/css/main.css` for the handoff panel, summary chips, preview block, and responsive wrapping.
5. Add i18n strings in `static/js/i18n.js`.
6. Update `tests/test_settings_tab_refactor_frontend.py` to assert helper names, render order, copy hook, CSS hooks, i18n strings, secret-safety slices, and provider-agnostic behavior.
7. Run syntax, focused frontend tests, diff check, and browser overflow QA.

## Validation Commands

- `node --check static/js/main.js`
- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q`
- `git diff --check`

## Browser QA

Use the local Flask app to open Settings -> API Security on desktop and mobile viewports. Confirm the command center, handoff panel, preview code block, and copy button have zero page/panel horizontal overflow.

## Risk Points

- The handoff builder must not accidentally read `settingsExternalApiKey` or multi-key textarea values.
- Long URLs and JSON examples can overflow mobile if CSS does not set `min-width: 0`, `overflow-wrap`, and pre wrapping.
- Duplicating backend rules in the frontend would create drift; keep the handoff as a projection over existing manifest/quickstart/action-plan helpers.
- Render order matters because the Integration Bundle should remain the primary starting point.
