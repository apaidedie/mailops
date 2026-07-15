# External integration workflow playbooks UI implementation plan

## Steps

1. Read task artifacts plus frontend quality guidelines for external API starter/command center work.
2. Add workflow state and helpers in `static/js/main.js`: manifest workflow getter, fallback builder, workflow normalization, selected workflow management, rendered metadata formatting, and copy text generation.
3. Extend `renderExternalApiCommandCenter()` to render workflow selector, selected workflow steps, and a copy playbook button inside the existing command center.
4. Add delegated click handling for workflow selection and playbook copy.
5. Add CSS hooks in `static/css/main.css` for desktop/mobile layout, stable step rows, method badges, wrapping endpoints, and selected/focus states.
6. Add i18n strings in `static/js/i18n.js`.
7. Update frontend contract tests and API-backed secret-safety tests.
8. Run syntax checks, targeted tests, diff check, debug console scan, and DuckMail token scan.

## Validation Commands

- `node --check static/js/main.js`
- `python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_external_api.py tests/test_external_temp_emails_api.py tests/test_multi_mailbox.py -q`
- `git diff --check`
- `rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml outlook_web`

## Risk Points

- `static/js/main.js` is large; keep changes near existing external API starter helpers to avoid scattering command-center logic.
- Contract tests inspect source slices, so function names and secret-safe boundaries should be stable and easy to assert.
- Long workflow endpoints and request metadata can overflow mobile if CSS does not wrap aggressively.
- Fallback playbooks must stay provider-agnostic and endpoint-map driven.
