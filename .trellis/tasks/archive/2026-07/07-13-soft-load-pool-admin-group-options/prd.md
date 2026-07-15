# Soft-load pool-admin group options via loadGroups

## Problem

`ensurePoolAdminGroupOptions` always raw-fetches `/api/groups` even when the
global `groups` array is warm and `loadGroups` already soft-loads/coalesces.

## Goal

1. Prefer warm `groups` / soft `loadGroups(false)`.
2. No raw GET `/api/groups` in ensurePoolAdminGroupOptions.
3. forceRefresh still reloads via loadGroups(true) when needed.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] ensurePoolAdminGroupOptions uses warm groups / loadGroups
- [x] No fetch('/api/groups') in pool_admin.js (except mutations if any)
- [x] Focused tests green
