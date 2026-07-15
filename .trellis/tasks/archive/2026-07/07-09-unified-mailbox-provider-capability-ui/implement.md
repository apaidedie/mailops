# Implement

## Checklist

- [x] Start the task after planning artifacts are present.
- [x] Update provider capability normalizers in `static/js/features/mailboxes.js` to prefer `readiness_summary.capability_matrix`.
- [x] Render workflow summary chips, selector hints, read/lifecycle actions, configuration counts, inventory, and endpoint hints.
- [x] Add CSS hooks for workflow/selector/action/endpoint rows and mobile wrapping.
- [x] Update `tests/test_unified_mailbox_frontend_contract.py` to assert matrix-first rendering, fallback behavior, and secret safety.
- [x] Run focused frontend contract tests.
- [x] Run `git diff --check`.

## Validation Results

- `node --check static/js/features/mailboxes.js`
- `node --check static/js/i18n.js`
- `python -m pytest tests/test_unified_mailbox_frontend_contract.py -q` -> 8 passed
- `python -m pytest tests/test_external_api.py -q -k "provider_capability_matrix or provider_readiness or integration_bundle or openapi"` -> 4 passed
- `python -m pytest tests/test_unified_mailbox_catalog.py -q -k "provider_context or readiness"` -> 1 passed
- `git diff --check` -> passed
- Browser QA on `127.0.0.1:5107`: provider matrix reached `ready`, rendered 16 provider rows and 5 workflow summary items, desktop/mobile page and matrix overflow were 0, and browser console errors were 0.

## Validation Commands

```bash
python -m pytest tests/test_unified_mailbox_frontend_contract.py -q
git diff --check
```

## Rollback Points

- If the matrix projection breaks the unified page, revert the `mailboxes.js` renderer changes while keeping task artifacts.
- If CSS causes mobile overflow, keep the JavaScript data-source change and simplify the added visual hooks to one-column stacked details.

## Risk Notes

- Do not read Settings credential inputs or display secret values.
- Do not branch on provider names such as DuckMail, Mail.tm, TempMail.lol, Emailnator, or GPTMail.
- Keep dynamic strings escaped before writing `innerHTML`.
