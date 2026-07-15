# Soft-load and coalesce failed refresh list fetches

## Problem

`autoLoadFailedListIfNeeded` and `loadFailedLogs` both always GET
`/api/accounts/refresh-logs/failed` with no shared cache. Re-opening the
refresh modal or calling loadFailedLogs after auto-load duplicates network work.

## Goal

1. Shared soft cache + in-flight coalesce for failed refresh logs.
2. autoLoadFailedListIfNeeded and loadFailedLogs use the shared helper.
3. Invalidate/force after refresh mutations that change failed set.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Single helper owns raw GET refresh-logs/failed
- [x] Soft re-use warm cache when !force
- [x] Mutations force or invalidate
- [x] Focused tests green
