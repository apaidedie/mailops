# Fix Settings page path for deferred init and surface gates

## Problem

Primary Settings UX is `#page-settings` via `navigate('settings')` → `loadSettings()`,
not only `#settingsModal`. Recent deferrals/gates only treated the modal as active:

1. `initTempMailProviderOptions` / `initUpdateMethodConfigToggles` run in `showSettingsModal`
   but not on the page path → radios/toggles never bind when users open Settings from nav.
2. `refreshSettingsProviderSurfaces` / language-change gates use `isSettingsModalVisible()`
   only → catalog refresh skips Settings page surfaces while on `#page-settings`.

## Goal

1. Treat Settings as active when modal is open **or** `#page-settings` is the current page.
2. Ensure Settings-only inits run for both modal and page open paths.
3. Keep boot free of Settings-only inits and keep closed-state gates.

## Acceptance Criteria

- [x] `isSettingsSurfaceActive()` covers modal + page-settings
- [x] `loadSettings` / page open ensures temp-mail radios + update-method toggles init
- [x] Catalog/language refresh still gates on Settings surface active (not modal-only)
- [x] Focused tests + `node --check` + `git diff --check` pass
