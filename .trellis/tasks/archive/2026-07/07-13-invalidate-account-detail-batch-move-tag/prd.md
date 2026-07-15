# Invalidate account detail cache on batch move/tag

## Problem

`showEditAccountModal` soft-loads warm detail, but batch move-group and batch
tag paths do not invalidate `accountDetailCache`, so re-open can paint stale
`group_id` after bulk move.

## Goal

1. `confirmBatchMoveGroup` success invalidates affected accountIds.
2. `confirmBatchTag` success invalidates affected accountIds (consistency).
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] batch move invalidates
- [x] batch tag invalidates
- [x] contract asserts >= 5 call sites
- [x] Focused tests green
