# Settings save payload consolidation

## Goal

Make Settings save behavior easier to extend as more mailbox providers are added. The manual Save Settings flow and tab-switch auto-save flow should reuse the same frontend payload builders for shared settings sections so provider credentials, JSON fields, masked placeholders, and clear-empty semantics cannot drift between the two save paths.

## Background

The current provider platform already supports `legacy_bridge`, `cloudflare_temp_mail`, `mail_tm`, `duckmail`, `tempmail_lol`, `emailnator`, and plugin providers. Settings UI code in `static/js/main.js` now has two save paths:

- `saveSettings()` builds the full settings payload.
- `autoSaveSettings(tabName)` builds a partial payload when leaving a tab.

Recent audit found duplicated logic for temp-mail provider fields, provider credential placeholders, Emailnator JSON fields, CF Worker JSON fields, and external API multi-key handling. That duplication is a maintainability risk because future provider work may update one path and miss the other.

## Requirements

- Keep existing backend behavior and provider selection contracts unchanged.
- Keep the UI layout unchanged in this task.
- Extract shared frontend helpers in `static/js/main.js` for repeated settings payload assembly where it is already used by both manual save and auto-save.
- Preserve masked-secret placeholder behavior. Existing masked values must not be written back as new secrets.
- Preserve empty-value semantics used by the full save path, including clearing multi-key configuration when the editor is emptied and retaining defaults for empty JSON provider settings where the current full save already provides them.
- Auto-save should reuse the same helper path for the temp-mail and API Security tabs instead of maintaining parallel provider/API payload branches.
- Add or strengthen frontend contract tests so future edits cannot silently reintroduce divergent save logic.
- Keep production static JavaScript free of `console.log` and `console.debug`.
- Do not introduce real DuckMail tokens or any provider secret values into code, tests, docs, or task notes.

## Acceptance Criteria

- `static/js/main.js` exposes shared helper functions for collecting temp-mail settings and API Security settings payloads.
- `saveSettings()` uses the shared helpers for those sections.
- `autoSaveSettings('temp-mail')` and `autoSaveSettings('api-security')` use the same shared helpers instead of duplicating field-level provider credential and JSON parsing logic.
- Frontend contract tests assert the shared helper names and assert `autoSaveSettings` calls them rather than carrying its own DuckMail, Emailnator, CF Worker, or external multi-key field parsing branches.
- `node --check static/js/main.js` passes.
- Relevant settings/provider frontend tests pass.
- Secret and debug-log scans remain clean.

## Out Of Scope

- Backend provider selection changes.
- New provider support.
- Visual redesign of Settings.
- Browser screenshot QA, unless layout changes are introduced unexpectedly.
