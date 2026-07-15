# Preload provider catalog on app boot

## Goal

Load the mailbox provider catalog during app startup so account cards, import flows, pool admin filters, and Settings suggestions can resolve labels/options without waiting for Settings or soft-load races.

## Confirmed Facts

- `loadMailboxProviderCatalog()` currently runs from Settings load, temp-mail tab autosave, settings save, and temp-email page.
- Account-card labels now depend on `mailboxProviderCatalogCache` and soft-load when empty, then repaint after catalog arrives.
- Boot path (`DOMContentLoaded`) loads groups/tags/overview but not the provider catalog.
- Catalog endpoint is secret-free and already used by multiple UI surfaces.

## Requirements

- Trigger a non-blocking catalog preload during `DOMContentLoaded` init.
- Keep existing success-path refresh of account tags / settings UI.
- Do not block CSRF/layout/group loading; catalog load may run in parallel after core init starts.
- Contract test asserts boot path calls `loadMailboxProviderCatalog`.

## Acceptance Criteria

- [x] App boot path invokes provider catalog load.
- [x] Existing catalog consumers continue to work with cached data sooner.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Eager network probing (`probe_network`).
- Changing catalog payload shape.
- Preloading full mailbox inventories.
