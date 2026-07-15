# Defer plugin list ensure until temp-mail settings tab

## Problem

`ensureSettingsSurfaceReady()` always awaits `PluginManager.ensureLoaded()` on every
Settings open (including Basic tab). That can hit `/api/plugins` even when the user
only needs password/basic settings. Plugin list is only required for temp-mail
routing, plugin card, and schema/plugin dual-path UI.

## Goal

1. Remove plugin ensure from the shared Settings surface bootstrap.
2. Soft-load plugins when entering temp-mail tab (already present) and when
   `loadSettings` runs while already on temp-mail.
3. Keep plugin-card expand / lifecycle force paths.

## Acceptance Criteria

- [x] `ensureSettingsSurfaceReady` does not call PluginManager.ensureLoaded
- [x] temp-mail tab switch still ensures plugins
- [x] loadSettings on temp-mail still ensures plugins
- [x] Focused tests + node --check + git diff --check pass
