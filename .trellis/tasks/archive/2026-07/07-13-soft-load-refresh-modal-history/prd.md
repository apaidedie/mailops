# Soft-load refresh modal history list

## Problem

`loadRefreshLogs()` (refresh modal history, limit=1000) always GETs network,
while the page-level `loadRefreshLogPage` already soft-loads. Re-opening modal
history after a recent load duplicates work.

## Goal

1. Soft-load modal history via dedicated cache + optional in-flight coalesce.
2. Invalidate modal history when refresh-log page cache is invalidated.
3. forceRefresh still available.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadRefreshLogs soft-loads warm cache by default
- [x] invalidateRefreshLogPageCache also clears modal history cache
- [x] Focused tests green
