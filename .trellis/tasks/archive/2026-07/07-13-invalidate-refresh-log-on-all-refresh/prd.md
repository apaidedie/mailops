# Invalidate refresh-log cache on all refresh success paths

## Problem

Soft-load for refresh-log only invalidates on `refreshAllAccounts` complete.
Single-account retry and selected-batch refresh can write new log rows while
the soft cache still paints stale data on re-entry.

## Goal

1. Invalidate refresh-log cache after any successful refresh mutation path.
2. Keep navigate soft-load behavior.
3. Contract tests cover the invalidation call sites.

## Acceptance Criteria

- [x] retrySingleAccount success invalidates cache
- [x] batch selected refresh complete invalidates cache
- [x] refreshAllAccounts still invalidates
- [x] Focused tests green
