# Unified mailbox workspace first impression polish implementation plan

## Checklist

- Update the sidebar mailbox nav label and mailbox mode switcher labels so unified workspace is first and account-focused modes remain available.
- Change the mailbox view-mode fallback from `standard` to `unified` while keeping valid stored preferences.
- Update topbar copy and unified command-center microcopy to reinforce the unified mailbox workspace model.
- Add or adjust i18n strings for the new copy.
- Extend frontend contract tests for default mode, labels, and secret-safe/provider-agnostic constraints.
- Run static JS checks, focused frontend contract tests, and rendered desktop/mobile QA for the mailbox page.

## Validation commands

```bash
node --check static/js/main.js
node --check static/js/features/mailbox_compact.js
node --check static/js/features/mailboxes.js
node --check static/js/i18n.js
python -m pytest tests/test_unified_mailbox_frontend_contract.py tests/test_v191_compact_mode_frontend_contract.py tests/test_v191_compact_mode_behavior_node.py -q -rs
```

## Rendered QA

Use the running Flask app or start one on an open local port. Log in with the local `.env` password, open the mailbox page, and check desktop and mobile widths. Evidence should include page-level overflow values and visibility of `#unifiedMailboxCommandCenter` while the default mode is unified.

## Risk points

- Do not remove standard or compact mode values.
- Do not add provider-specific frontend branches or secret field reads.
- Do not let desktop grid placement create implicit mobile columns.
