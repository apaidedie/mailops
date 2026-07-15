# Implementation Plan

1. Update `templates/index.html` active-providers form group: neutral hint + chips mount.
2. Add getters/renderers/toggle helpers in `main.js`; call after catalog load.
3. Wire textarea `input` to re-sync chip active state.
4. Extend settings frontend contract tests.

## Validation

- `python -m unittest tests.test_settings_tab_refactor_frontend -q`
- `node --check static/js/main.js`
- `git diff --check`
