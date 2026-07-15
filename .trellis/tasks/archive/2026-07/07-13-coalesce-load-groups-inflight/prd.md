# Coalesce concurrent loadGroups fetches

## Problem

Cold `loadGroups()` always starts a new GET `/api/groups`. Rapid double entry
(mailbox navigate + compact mode switch, or import + UI refresh) can race two
identical network loads before the warm soft-load path applies.

## Goal

1. Share one in-flight promise for concurrent soft/cold network loads.
2. Soft warm-array path still short-circuits without network.
3. forceRefresh starts its own request (or safely shares when appropriate).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] groupsLoadPromise coalesces concurrent network loads
- [x] Warm soft path unchanged
- [x] forceRefresh still works
- [x] Focused tests green
