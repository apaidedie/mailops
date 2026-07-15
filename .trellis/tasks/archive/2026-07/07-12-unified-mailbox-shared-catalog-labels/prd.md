# Unified mailbox uses shared catalog labels

## Goal

Resolve unified-mailbox card and preview provider display names through the shared catalog label helper so they stay consistent with account cards, import, pool admin, and temp-email UI.

## Confirmed Facts

- Unified mailbox API already returns `provider_label` on directory items.
- Shared `resolveMailboxProviderLabel` is the frontend label owner for other surfaces.
- Cards currently use `item.provider_label || item.provider` only; catalog soft-load can improve missing/stale labels when API label is empty.

## Requirements

- Prefer shared catalog resolution for display labels when available.
- Keep API `provider_label` as the primary payload fallback via `fallbackResolver`.
- Apply to card render and preview mailbox label helpers.
- Contract tests assert shared-helper usage in `mailboxes.js`.

## Acceptance Criteria

- [x] Unified mailbox card/preview provider labels prefer shared catalog resolution.
- [x] Empty catalog still falls back to API `provider_label` / provider key.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing `/api/mailboxes` payload shape.
- Redesigning unified mailbox card layout.
