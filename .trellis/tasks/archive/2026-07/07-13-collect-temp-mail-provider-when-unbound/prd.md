# Collect temp-mail provider from pending/snapshot when radios unbound

## Problem

After deferring temp-mail radio init, global `saveSettings()` always calls
`collectTempMailSettingsPayload()`. When radios were never bound, it fell back
to `getOperatorDefaultTempMailProvider()` and could overwrite the stored
`temp_mail_provider` with the operator default (e.g. `legacy_bridge`) even if
the server value was a different configured provider.

## Goal

1. Collect provider from checked radio when present.
2. Else pending mount value, else snapshot, else operator default.
3. Keep dirty-key schema collection (no phantom field writes when unbound).

## Acceptance Criteria

- [x] collectTempMailSettingsPayload prefers pending/snapshot over bare default when unbound
- [x] checked radio still wins when present
- [x] Focused tests + node --check + git diff --check pass
