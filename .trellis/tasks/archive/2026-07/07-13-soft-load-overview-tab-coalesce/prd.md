# Coalesce concurrent overview tab loads

## Problem

`loadOverviewTab` uses a boolean `loading[tabId]` and early-returns without
sharing the in-flight promise. Concurrent soft/force opens can drop work or
race, and callers cannot await a shared request.

## Goal

1. Soft-load warm `__overviewState.cache[tabId]` when !forceReload.
2. Coalesce concurrent loads via `loadPromises[tabId]`.
3. forceReload still networks (after coalesce if already in-flight).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadPromises map
- [x] Soft cache hit + coalesce
- [x] force path still fetches
- [x] Focused tests green
