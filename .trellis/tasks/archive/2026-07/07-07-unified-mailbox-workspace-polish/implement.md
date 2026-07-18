# Unified mailbox workspace polish implementation

## Checklist

- [x] Read frontend quality guidelines, backend provider-selection contract, code-reuse guide, and cross-layer guide before editing.
- [x] Extend `static/js/features/mailboxes.js` with command-center quick-view model/render helpers that consume `getUnifiedQuickViewPresets(contract)`.
- [x] Route command-center quick-view clicks through `applyUnifiedQuickView(key)` and keep the existing quick-view row behavior unchanged.
- [x] Polish loading, error, ready, hover, focus, active, and mobile styles in `static/css/main.css` without adding new libraries.
- [x] Add any new copy to `static/js/i18n.js`.
- [x] Update `tests/test_unified_mailbox_frontend_contract.py` for helper names, markup hooks, CSS hooks, i18n strings, and secret-safety.
- [x] Run syntax checks, targeted pytest, whitespace check, token scan, debug-console scan, and rendered desktop/mobile checks.

## Validation Commands

- `node --check static/js/features/mailboxes.js`
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_unified_mailbox_catalog.py -q`
- `git diff --check`
- `rg -n "dk_[0-9a-fA-F]{20,}|DUCKMAIL_BEARER_TOKEN\s*=\s*dk_|Bearer\s+dk_" templates static tests .trellis docs README.md README.en.md .env.example docker-compose.yml mailops`
- `rg -n "console\.(log|debug)" static\js -g '!tests/layout-system/coverage/**'`

## Rollback Points

- Revert `static/js/features/mailboxes.js` if command-center quick-view clicks disturb the existing filter or stale-response flow.
- Revert command-center CSS changes if browser QA shows mobile overflow or desktop overlap.
