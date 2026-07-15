# Temp email UI uses shared catalog labels

## Goal

Route temp-email create UI provider display labels through the shared catalog helper so status text and domain hints stay consistent with account cards, import, and pool admin.

## Confirmed Facts

- `getTempEmailProviderDisplayLabel` already prefers `getMailboxProviderCatalogItem(..., 'temp')`.
- Shared helpers `resolveMailboxProviderLabel` / `getMailboxProviderCatalogLabel` now own account/import/pool label lookup.
- Temp catalog items can live in a different cache slice than account catalog; prefer temp catalog item first, then shared resolve.

## Requirements

- Prefer catalog-backed labels for temp-email provider status and option hints.
- When shared resolve exists, use it after temp catalog item lookup (or as unified fallback) so soft-load behavior is consistent.
- Keep select-option text and options payload fallbacks when catalog is empty.
- Contract tests assert shared-label usage from `temp_emails.js`.

## Acceptance Criteria

- [x] Temp-email provider display labels prefer shared catalog resolution when available.
- [x] Existing status/options fallbacks still work without catalog cache.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing temp-email create API or domain strategy behavior.
- Unifying plugin config save path with `/api/settings`.
