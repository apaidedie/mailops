# Unified mailbox quick views

## Goal

Add data-driven quick view presets to the unified mailbox directory so users can switch common aggregation workflows without manually composing filters.

## Confirmed Facts

- Unified mailbox mode already calls `/api/mailboxes` and keeps filters in `unifiedMailboxState.filters`.
- The existing API contract supports `kind`, `status`, `read_capability`, `action`, `provider`, `sort`, and `search` query parameters.
- The current unified toolbar exposes those fields as individual controls, but it does not provide one-click workflow presets.
- This task is a UI/UX and frontend state improvement; it should not add backend fields or change provider selection semantics.

## Requirements

- Add a compact quick-view preset row to the unified mailbox directory near the existing unified toolbar.
- Presets must be data-driven from the existing filter contract, not provider-specific hardcoded branches.
- Include useful default workflows for mailbox aggregation such as all mailboxes, Outlook/IMAP accounts, temp mailboxes, readable mailboxes, and items that need attention.
- Applying a quick view must update the existing filter controls, reset pagination to page 1, and call the existing unified mailbox loader.
- Preserve manual filter use; if the user changes any individual filter/search field, the active quick-view state must reflect custom filtering instead of lying about a preset being active.
- Keep layout compact, professional, keyboard-accessible, and responsive on mobile.
- Do not read or expose provider secret inputs, API keys, task tokens, refresh tokens, passwords, JWTs, consumer keys, or bearer tokens.

## Acceptance Criteria

- [ ] `templates/index.html` exposes a quick-view container inside the unified mailbox layout.
- [ ] `static/js/features/mailboxes.js` defines reusable quick-view presets and applies them through the existing `unifiedMailboxState.filters` path.
- [ ] Quick-view buttons visibly mark the active preset and fall back to a custom state when filters do not match a preset.
- [ ] Presets do not branch on built-in provider names such as `duckmail`, `mail_tm`, `emailnator`, or `gptmail`.
- [ ] Existing provider facet chips, capability matrix, result bar, pagination, and open-mailbox flows continue to work.
- [ ] Frontend contract tests cover DOM mounts, preset definitions, apply/sync helpers, event delegation, secret-safety, i18n strings, and CSS hooks.
- [ ] `python -m pytest tests/test_unified_mailbox_frontend_contract.py -q` passes.
- [ ] Relevant syntax/static checks and debug/secret scans pass.

## Notes

- UI brief: operational SaaS, dense but calm, workspace-first. Primary workflow is switching between common mailbox aggregation perspectives without forcing users to compose six controls manually.
