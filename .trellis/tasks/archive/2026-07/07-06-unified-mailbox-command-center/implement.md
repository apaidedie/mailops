# Unified mailbox command center implementation

## Checklist

- Add `#unifiedMailboxCommandCenter` to the unified mailbox layout before the toolbar.
- Add `renderUnifiedCommandCenter()` and small helper formatters in `static/js/features/mailboxes.js`.
- Call the renderer from loading, error, and success paths in `loadUnifiedMailboxes()`.
- Add CSS for command-center shell, metrics, route summary, workflow chips, focus/hover, and mobile stacking.
- Add i18n entries for all new labels and fallback text.
- Extend `tests/test_unified_mailbox_frontend_contract.py` for DOM, JS, CSS, and i18n contracts.
- Run syntax and targeted frontend/backend unified mailbox tests.

## Validation Commands

```powershell
node --check static/js/features/mailboxes.js
$env:PYTHONIOENCODING='utf-8'; python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_unified_mailbox_catalog.py -q
```

If rendered UI startup is cheap, run a desktop/mobile browser check for unified mode.

## Risk Notes

The main risk is duplicating backend routing/provider rules in frontend copy. Keep the command center as a display adapter over `/api/mailboxes` fields.

The second risk is turning an operational workspace into a decorative hero. Keep the section compact and dense enough that filters and results remain visible on normal desktop screens.
