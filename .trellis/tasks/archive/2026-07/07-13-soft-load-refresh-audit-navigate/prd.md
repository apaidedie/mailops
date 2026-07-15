# Soft-load refresh-log and audit pages on navigate

## Problem

`loadRefreshLogPage` / `loadAuditLogPage` always clear the container and fetch
network data on every navigate, even when the operator just left and returned.

## Goal

1. Soft-load with short-lived in-memory payload cache on re-entry.
2. Force-refresh still available via `forceRefresh=true` and after full token refresh.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Both loaders accept forceRefresh and reuse warm cache when soft
- [x] navigate keeps soft load (default)
- [x] refreshAllAccounts invalidates refresh-log cache
- [x] Focused tests green
