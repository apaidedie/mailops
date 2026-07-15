# Defer Settings tab control init until each tab is opened

## Problem

`ensureSettingsSurfaceReady()` still initializes temp-mail provider radios and
automation update-method toggles on every Settings open, including Basic tab.

## Goal

1. Init temp-mail radios only on temp-mail tab (with plugin ensure).
2. Init update-method toggles only on automation tab.
3. loadSettings may set pending provider values without painting temp-mail when on other tabs.
4. Tab switch rehydrates the opened tab from snapshot/caches.

## Acceptance Criteria

- [x] ensureSettingsSurfaceReady does not init temp-mail radios or update-method toggles
- [x] temp-mail tab switch/load inits radios + plugins and hydrates selection
- [x] automation tab switch/load inits update-method toggles
- [x] Focused tests + node --check + git diff --check pass
