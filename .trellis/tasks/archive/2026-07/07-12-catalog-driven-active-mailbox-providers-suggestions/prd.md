# Catalog-driven active mailbox providers suggestions

## Goal

Remove hard-coded provider name hints from Settings “启用邮箱来源” and offer catalog-driven suggestions so operators can pick valid allowlist values without memorizing keys.

## Confirmed Facts

- `#activeMailboxProviders` is a free-text textarea; lines become `active_mailbox_providers` on save.
- Empty value means all providers enabled.
- Backend selection_policy exposes `scopes.active_allowlist.allowed_values` and `settings_key=active_mailbox_providers`.
- Frontend already caches `mailboxProviderSelectionPolicyCache` from `/api/providers`.
- Native HTML datalist does not attach to textarea; suggestions need chips or a companion picker.

## Requirements

- Soften template hint/placeholder so it no longer hard-codes specific provider names as the only guidance.
- Render clickable suggestion chips from `selection_policy.scopes.active_allowlist.allowed_values` (skip empty/`auto`).
- Clicking a chip toggles that provider line in the textarea (add if missing, remove if present).
- Refresh chips when catalog/selection_policy loads.
- Keep free-text editing and existing save/load semantics.
- Update frontend contract tests.

## Acceptance Criteria

- [x] Template no longer presents a fixed hard-coded provider roster as the primary guidance text.
- [x] Chips/suggestions are populated from selection policy allowed values.
- [x] Chip click toggles the corresponding line in `#activeMailboxProviders`.
- [x] Existing textarea save/load still works.
- [x] Focused frontend tests + `git diff --check` pass.

## Out Of Scope

- Replacing textarea with multi-select component redesign.
- Backend allowlist validation changes.
- Import-account provider dropdown work (already partially dynamic).
