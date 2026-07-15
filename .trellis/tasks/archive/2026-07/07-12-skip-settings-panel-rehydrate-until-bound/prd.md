# Skip Settings panel rehydrate on catalog load until bound

## Problem

After deferring Settings radio init, catalog success/error still calls
`onTempMailProviderChange` / `renderTempMailProviderConfigPanel` on every
`/api/providers` soft-load — rewriting hidden Settings config panels before
the user opens Settings.

## Goal

1. Only rehydrate Settings temp-mail selection/config panel when the Settings
   provider mount has been bound (opened at least once).
2. Keep non-Settings catalog consumers (tags, pool, import, unified labels) active.

## Acceptance Criteria

- [x] Catalog success/error does not call Settings panel rehydrate when unbound
- [x] After Settings open (bound), catalog refresh still rehydrates selection/panel
- [x] Focused tests + `node --check` + `git diff --check` pass
