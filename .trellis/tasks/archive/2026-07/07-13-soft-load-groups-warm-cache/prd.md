# Soft-load groups list when warm cache exists

## Problem

`loadGroups()` always shows loading and GETs `/api/groups`, even when `groups`
is already warm (mailbox re-entry with groups.length>0 is gated, but other
callers still force network).

## Goal

1. `loadGroups(forceRefresh=false)` reuses warm `groups` array and re-renders.
2. Mutation paths pass `forceRefresh=true`.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft load when groups array non-empty and !force
- [x] Mutation call sites force refresh
- [x] Focused tests green
