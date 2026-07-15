# Refresh settings snapshot after temp-mail save

## Goal

After temp-mail Settings save (manual or auto-save), refresh `tempMailSettingsSnapshot` / dirty keys from `/api/settings` so schema panel secret hints and configured badges match server state (including `plugin.*` keys).

## Problem / evidence

- Schema collectors use dirty-key + snapshot for secrets (`*_set` / `*_masked`).
- Successful save currently refreshes catalog but not the settings snapshot, so secret fields may still look "未设置" and dirty keys can re-submit stale values on next tab switch.

## Requirements

- After successful temp-mail save, reload settings into snapshot and clear dirty keys.
- Rehydrate / re-render the current schema panel when open.
- Manual save and auto-save both covered.
- Contract tests assert the refresh helper call sites.

## Acceptance Criteria

- [x] Helper reloads `/api/settings` into `tempMailSettingsSnapshot` and clears dirty keys.
- [x] Manual + auto save temp-mail paths invoke it after success.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing save payload shape.
- Full settings modal UI redesign.
