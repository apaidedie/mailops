# Implementation Plan

## Implementation steps

1. Inspect the current unified mailbox template, CSS, JavaScript render helpers, i18n entries, and frontend contract tests.
2. Add a compact workspace masthead and product framing inside `#mailboxUnifiedLayout` without removing existing control IDs.
3. Polish unified workspace CSS: shell background, command center hierarchy, toolbar wrapping, quick-view states, result bar, provider panels, capability matrix, mailbox cards, focus states, reduced-motion rules, and mobile collapse rules.
4. Improve JavaScript-rendered copy or classes only where it materially improves the unified workspace and stays backend-contract-driven.
5. Update frontend contract tests if new persistent hooks or acceptance-relevant CSS are added.
6. Run scoped tests, then run a rendered browser check for desktop and mobile overflow and key widths.
7. Update frontend spec only if a new repeatable guideline is discovered.
8. Commit the task and archive it through Trellis.

## Validation commands

`python -m pytest tests/test_unified_mailbox_frontend_contract.py -q`

If JavaScript behavior changes materially, also run relevant browser-extension/node tests only when touched. If backend is untouched, do not run the full backend suite unless a scoped failure suggests cross-layer risk.

Rendered UI validation should start the Flask app in a local process, login through the test password if needed, navigate to unified mailbox mode, and check desktop and mobile dimensions for page-level overflow and `.unified-toolbar` internal overflow.

## Risk points

`templates/index.html` has many existing IDs and inline handlers. Preserve them.

`static/css/main.css` is large and has existing media queries around unified mailbox layout. Search before changing values and keep mobile overrides synchronized with desktop grid placement.

`static/js/features/mailboxes.js` has provider-agnostic safety tests. Do not add provider-name conditionals or secret input references.

## Rollback points

If visual CSS breaks broad pages, revert the unified `.mailbox-unified-*` and `.unified-*` edits first. If template hooks break tests, restore the original `#mailboxUnifiedLayout` structure and reapply only non-structural styling.
