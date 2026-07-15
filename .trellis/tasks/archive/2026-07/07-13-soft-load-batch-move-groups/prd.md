# Soft-load batch-move groups from warm groups cache

## Problem

`loadGroupsForBatchMove` always GETs `/api/groups` even when the global
`groups` array is warm and `loadGroups` already soft-loads/coalesces.

## Goal

1. Prefer warm `groups` / soft `loadGroups(false)`.
2. No raw GET in loadGroupsForBatchMove.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadGroupsForBatchMove uses loadGroups soft path
- [x] No fetch('/api/groups') inside loadGroupsForBatchMove
- [x] Focused tests green
