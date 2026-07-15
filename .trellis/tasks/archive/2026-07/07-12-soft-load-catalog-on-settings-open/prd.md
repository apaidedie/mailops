# Soft-load provider catalog when opening Settings if cache warm

## Problem

Boot already soft-preloads `/api/providers`. Opening Settings still calls
`loadMailboxProviderCatalog(true)` from `loadSettings`, forcing a second network
fetch every time even when the cache is warm.

Post-save and post-temp-mail-tab-save force refresh remains correct because
settings mutations may change catalog projections.

## Goal

1. Settings open (`loadSettings`) soft-loads catalog when warm; force only when
   cache is empty-array warm-but-empty.
2. Keep force refresh after settings save / temp-mail tab save.
3. Preserve DOM hooks and Settings hydration order.

## Acceptance Criteria

- [x] `loadSettings` does not always force catalog refresh
- [x] Empty warm cache still force-refreshes
- [x] Save paths still force-refresh catalog
- [x] Focused tests + `node --check` + `git diff --check` pass
