# Refresh account provider tags after catalog load

## Goal

Fix the first-paint race where account cards may show raw provider keys until a full re-render: after `/api/providers` catalog loads, re-render the current account list so tags pick up catalog labels immediately.

## Confirmed Facts

- `getProviderLabel()` already prefers `mailboxProviderCatalogCache` and soft-loads catalog when empty.
- Soft load does not re-render the already painted account list.
- `loadMailboxProviderCatalog()` success path already refreshes Settings/temp-mail UI but not mailbox account cards.
- Cached accounts live in `accountsCache[currentGroupId]`; `renderAccountList` / `renderCompactAccountList` can repaint without a network round-trip.

## Requirements

- On successful catalog load, if a current group account list is cached, re-render standard and compact account lists.
- Do not force a network reload of accounts.
- Keep failure path non-destructive (no erroneous re-render requirement).
- Contract test asserts the refresh call site exists in catalog load success path.

## Acceptance Criteria

- [x] Catalog load success path re-renders cached current-group account list when available.
- [x] Compact list refresh is included when the helper exists.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing account API payloads.
- Redesigning account cards.
- Global reactive store rewrite.
