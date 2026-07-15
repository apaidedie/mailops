# Defer Settings temp-mail provider options init until settings open

## Problem

Boot always calls `initTempMailProviderOptions()`, which binds + renders Settings
temp-mail radios even when the user never opens Settings. Catalog preload then
re-renders the same hidden mount again.

## Goal

1. Do not init/render Settings temp-mail provider radios on every page boot.
2. Init (bind + render) when Settings opens.
3. Catalog success only re-renders radios after options have been initialized
   (mount is bound) so hidden Settings DOM is not rewritten on every catalog load.

## Acceptance Criteria

- [x] DOMContentLoaded does not call `initTempMailProviderOptions()`
- [x] `showSettingsModal` calls `initTempMailProviderOptions()` before `loadSettings`
- [x] Catalog refresh still updates radios after Settings has been opened once
- [x] Focused tests + `node --check` + `git diff --check` pass
