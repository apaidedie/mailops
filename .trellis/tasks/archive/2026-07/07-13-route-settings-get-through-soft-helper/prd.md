# Route remaining settings GETs through soft-load helper

## Problem

Several code paths still raw-fetch GET `/api/settings` instead of
`fetchSettingsPagePayload`, causing duplicate network work and skipping the
soft-load / in-flight coalesce path. Also, invalidate-while-in-flight can
repopulate the cache with a pre-write payload.

## Goal

1. `refreshTempMailSettingsSnapshotFromServer` uses force helper fetch.
2. `initPollingSettings` fallback uses soft helper fetch.
3. `triggerUpdate` uses soft helper fetch for update_method.
4. Invalidate bumps generation so stale in-flight responses do not repopulate cache.
5. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Remaining GET /api/settings (except helper itself) go through helper or intentional non-soft paths are documented
- [x] Generation guard on cache write
- [x] Focused tests green
