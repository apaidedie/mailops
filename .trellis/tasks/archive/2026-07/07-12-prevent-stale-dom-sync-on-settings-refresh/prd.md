# Prevent stale DOM sync when refreshing settings snapshot

## Goal

When reloading `tempMailSettingsSnapshot` from the server after save, do not re-read stale schema inputs back into the snapshot via `syncTempProviderSchemaInputsToSnapshot()`.

## Problem / evidence

- `renderTempMailProviderConfigPanel()` always calls `syncTempProviderSchemaInputsToSnapshot()` first to preserve in-progress edits when switching providers.
- `refreshTempMailSettingsSnapshotFromServer()` assigns server settings then calls `renderTempMailProviderConfigPanel()`, which syncs empty/stale secret inputs over the fresh snapshot and can re-dirty keys.

## Requirements

- Allow schema panel re-render with `skipSnapshotSync` for server-authoritative reloads.
- Refresh helper uses skip path.
- Provider change / normal re-render still preserves edits.
- Contract tests assert the option and call site.

## Acceptance Criteria

- [x] `renderTempMailProviderConfigPanel` supports skipping snapshot sync.
- [x] Server refresh path uses skip.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing dirty-key collection semantics for user edits.
