# Coalesce concurrent loadAccountsByGroup fetches

## Problem

`loadAccountsByGroup` soft-loads warm cache but cold network loads for the same
queryKey can race (navigate + selectGroup, compact re-render, force double-tap)
and stampede `/api/accounts`.

## Goal

1. Share one in-flight promise per queryKey for concurrent loads.
2. Warm soft path unchanged.
3. forceRefresh still networks (may share in-flight for same key when already loading).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] accountsByGroupLoadPromises coalesces by queryKey
- [x] Warm soft path still short-circuits
- [x] Focused tests green
