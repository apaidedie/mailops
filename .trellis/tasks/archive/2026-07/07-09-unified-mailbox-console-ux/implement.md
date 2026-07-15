# Unified Mailbox Console UX Implementation Plan

## Steps

- [x] Add the operational lens DOM mount in `templates/index.html`.
- [x] Add generic operational lens helpers and renderer in `static/js/features/mailboxes.js`.
- [x] Wire loading/error/ready render paths and event delegation for lens actions.
- [x] Add responsive CSS for `.unified-operational-lens` and child elements.
- [x] Add Chinese/English i18n entries for lens labels and states.
- [x] Extend `tests/test_unified_mailbox_frontend_contract.py` for the new DOM, JS, CSS, i18n, and secret-safety/provider-agnostic requirements.

## Validation Results

- `python -m pytest tests\test_unified_mailbox_frontend_contract.py -q` -> `8 passed`
- `python -m pytest tests\test_unified_mailbox_catalog.py tests\test_overview_frontend_contract.py -q` -> `19 passed`
- `python scripts\project_readiness_check.py` -> all readiness checks passed
- `git diff --check` -> no whitespace errors; only existing LF/CRLF conversion warnings
- Browser check on `http://127.0.0.1:5600/` with a temporary test database:
  - Desktop `1280x720`: page overflow `0`, lens overflow `0`, toolbar overflow `0`, lens rendered `3` cards and `1` action.
  - Mobile `390x844`: page overflow `0`, unified layout overflow `0`, lens overflow `0`, toolbar overflow `0`, command center overflow `0`, lens collapsed to one column.

## Validation Commands

```powershell
python -m pytest tests\test_unified_mailbox_frontend_contract.py tests\test_unified_mailbox_catalog.py -q
python -m pytest tests\test_overview_frontend_contract.py -q
python scripts\project_readiness_check.py
git diff --check
```

## Review Gates

- No backend API behavior changes.
- No provider-name conditionals inside operational lens helpers.
- No secret input IDs or credential values referenced by operational lens helpers.
- Mobile CSS uses auto-fit/minmax or single-column collapse, not fixed desktop-only columns.
- Existing command center, quick views, provider context, capability matrix, and mailbox cards still render in order.

## Rollback Points

- If tests show contract drift, revert only this task's template/JS/CSS/i18n/test changes.
- If rendered mobile layout overflows, adjust lens CSS before touching existing command-center layout.
