# Use operator default helper for remaining Settings fallbacks and defer update-method toggles

## Problem

1. Several Settings helpers still hard-code `'legacy_bridge'` as a fallback instead of
   `getOperatorDefaultTempMailProvider()` (catalog-backed operator default).
2. Boot still binds Settings "update method" radios via `initUpdateMethodConfigToggles()`
   even when Settings is never opened (same class of work as deferred temp-mail radios).

## Goal

1. Route remaining Settings provider-name fallbacks through `getOperatorDefaultTempMailProvider()`.
2. Defer `initUpdateMethodConfigToggles()` from boot to `showSettingsModal`.
3. Keep DOM hooks and Settings save/load behavior intact.

## Acceptance Criteria

- [x] Remaining Settings provider fallbacks use the operator default helper (not bare `'legacy_bridge'` literals in those call sites)
- [x] Boot does not call `initUpdateMethodConfigToggles()`
- [x] `showSettingsModal` calls `initUpdateMethodConfigToggles()` before `loadSettings`
- [x] Focused tests + `node --check` + `git diff --check` pass
