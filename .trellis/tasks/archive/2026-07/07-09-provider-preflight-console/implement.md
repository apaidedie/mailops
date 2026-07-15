# Provider preflight console implementation plan

## Steps

- [x] Add provider preflight mount points in `templates/index.html` inside `#providerWorkbench`.
- [x] Add preflight cache, loader, renderer, retry/probe action, and event delegation in `static/js/main.js`.
- [x] Wire loader calls into settings/provider catalog load, settings save refresh, and language-change render hooks.
- [x] Add responsive `provider-preflight-*` styles in `static/css/main.css`.
- [x] Add frontend contract tests for DOM hooks, JS helper names/endpoint usage, secret safety, provider-agnostic helpers, i18n strings, and CSS responsiveness.
- [x] Run syntax checks, targeted frontend contract tests, provider preflight backend tests, and visual/browser QA if a runnable server is available.

## Verification Results

- `python -m pytest tests/test_settings_tab_refactor_frontend.py -q` -> 27 passed, 4 subtests passed.
- `python -m pytest tests/test_multi_mailbox.py -k "provider_preflight" -q` -> 3 passed, 26 deselected.
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py -q` -> 8 passed.
- `python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_unified_mailbox_frontend_contract.py -q` -> 35 passed, 4 subtests passed.
- `python -m py_compile outlook_web\controllers\accounts.py outlook_web\routes\accounts.py outlook_web\services\provider_catalog.py` -> passed.
- `node --check static/js/main.js` and `node --check static/js/i18n.js` -> passed.
- `git diff --check` -> passed; Git reports existing LF-to-CRLF warnings for touched text files.
- Browser QA via Playwright against `http://127.0.0.1:5057/` -> desktop and mobile preflight panel rendered, page/panel/summary/list horizontal overflow all `0`; screenshots written under `output/playwright/` and left untracked.

## Spec Update Review

No `.trellis/spec/` update was needed. The feature follows existing frontend specs for Settings provider workbench UI consumption: authenticated backend payloads only, no credential input reads, no `/api/external/*` local readiness fetch, provider-agnostic helpers, and mobile-safe dense panels.

## Validation Commands

- `python -m py_compile outlook_web\\controllers\\accounts.py outlook_web\\routes\\accounts.py outlook_web\\services\\provider_catalog.py`
- `python -m pytest tests/test_settings_tab_refactor_frontend.py tests/test_unified_mailbox_frontend_contract.py -q`
- `python -m pytest tests/test_multi_mailbox.py -k "provider_preflight" -q`
- `git diff --check`

## Rollback

Remove the provider preflight DOM mount, JS loader/renderer/event hooks, CSS hooks, and tests together. The backend endpoint remains from the previous task.
