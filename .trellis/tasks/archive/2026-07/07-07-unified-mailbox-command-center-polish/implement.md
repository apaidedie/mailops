# Implementation Plan

## Steps

1. Inspect current command-center render, template, CSS, i18n, and focused tests against the frontend and provider-selection contracts.
2. Record any concrete gaps before editing. Prefer small fixes that improve command-center hierarchy, contract consumption, wrapping, or test coverage.
3. Implement scoped changes in the existing static JS/CSS/i18n files and update frontend contract tests.
4. Run focused tests and static checks.
5. Run rendered desktop and mobile QA if pixels or responsive behavior changed.
6. Commit the implementation, archive this child task, and record a session journal entry.

## Guardrails

- Do not read Settings credential inputs from command-center helpers.
- Do not branch on built-in provider names to decide routing, endpoints, or copy.
- Do not leak provider secret values into code, tests, docs, logs, screenshots, or final output.
- Do not change backend provider selection semantics unless the audit proves a backend contract gap.
- Keep unrelated Trellis tasks and user changes untouched.

## Checks

- `python -m pytest tests/test_unified_mailbox_frontend_contract.py -q -rs`
- `python -m pytest tests/test_unified_mailbox_catalog.py -q -rs`
- `node --check static/js/features/mailboxes.js`
- `node --check static/js/i18n.js`
- Secret scan for DuckMail/API-key patterns.
- `git diff --check`
- Rendered browser QA on desktop and mobile when UI files change.
