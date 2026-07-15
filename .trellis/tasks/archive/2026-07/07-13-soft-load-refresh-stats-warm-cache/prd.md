# Soft-load refresh stats when warm cache exists

## Problem

`loadRefreshStats()` always GETs `/api/accounts/refresh-stats`, including when
re-opening the refresh modal after a recent load with no intervening mutations.

## Goal

1. Soft-load via warm payload cache + in-flight coalesce.
2. Force-refresh after refresh/retry/batch delete / invalid-token governance.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadRefreshStats(forceRefresh=false) reuses warm cache
- [x] Mutation/refresh paths pass force true
- [x] showRefreshModal uses soft load
- [x] Focused tests green
