# Defer plugin list load until needed

## Goal

Stop PluginManager from fetching `/api/plugins` on every page boot. Load the plugin list when Settings opens (or the plugin card is expanded).

## Evidence

- `PluginManager.init()` always calls `loadPlugins()` on DOMContentLoaded.
- Users who never open Settings/plugins still pay for `/api/plugins` (+ soft catalog follow-up) on every page load.
- `toggleCard()` already lazy-loads when the card expands and `_plugins` is empty.

## Requirements

- `init()` must not auto-load plugins.
- `showSettingsModal` ensures plugins are loaded before/with settings so schema routing + inject fallbacks work.
- Opening temp-mail settings tab also ensures load if list empty.
- Manual refresh / install / uninstall / applyChanges still load as today.
- Contract tests assert deferred init + settings ensure-load markers.

## Acceptance Criteria

- [x] Plugin init no longer calls loadPlugins unconditionally.
- [x] Settings open path ensures plugin list load.
- [x] Focused tests + `git diff --check` pass.
