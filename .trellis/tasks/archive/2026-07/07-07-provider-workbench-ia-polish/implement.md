# Implementation Plan

## Steps

1. Read frontend quality guidelines and provider workbench specs before editing.
2. Inspect current `templates/index.html`, `static/js/main.js`, `static/css/main.css`, and frontend contract tests for provider workbench behavior.
3. Update the provider workbench shell copy and overview render output while keeping existing cache-driven data flow.
4. Refine CSS for the operations-console overview, stable metric tiles, details sections, and mobile wrapping.
5. Update frontend contract tests for new copy/hooks and secret-safety coverage.
6. Run focused frontend tests, JS syntax checks, browser QA screenshots, secret scan, `git diff --check`, and full pytest if the focused suite is green.
7. Commit, archive the child task, and record the journal.

## Checks

- `python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_unified_mailbox_frontend_contract.py -q -rs`
- `node --check static/js/main.js`
- `node --check static/js/i18n.js`
- Browser QA on Settings -> API Security at desktop and mobile widths.
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\\s*=\\s*dk_|Bearer\\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml mailops`
- `git diff --check`
- `python -m pytest -q -rs`

## Guardrails

- Do not change provider aliases, env keys, request fields, or endpoint paths.
- Do not read secret form input values to render the overview.
- Do not hardcode provider-specific routing logic in the frontend.
- Do not add nested cards inside the workbench shell.
