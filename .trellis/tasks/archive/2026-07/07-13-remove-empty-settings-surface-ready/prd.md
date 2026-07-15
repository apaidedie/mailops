# Remove empty ensureSettingsSurfaceReady stub

## Problem

`ensureSettingsSurfaceReady()` is an empty async stub still awaited from
`showSettingsModal` and `loadSettings`. Tab init was deferred earlier; the stub
adds noise and false signal of shared bootstrap work.

## Goal

1. Remove the empty function and its call sites.
2. Keep tab-specific init (`ensureTempMailSettingsTabReady` /
   `ensureAutomationSettingsTabReady`) on loadSettings / tab switch.
3. Preserve Settings page + modal open behavior (loadSettings still runs).

## Acceptance Criteria

- [x] No `ensureSettingsSurfaceReady` in main.js
- [x] Modal still calls `loadSettings()`; page path still loads settings
- [x] Focused contract tests + node --check + git diff --check pass
