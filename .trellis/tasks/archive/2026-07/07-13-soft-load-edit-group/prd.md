# Soft-load editGroup from warm groups cache

## Problem

`editGroup` always GETs `/api/groups/<id>` even when the warm `groups` array
already has the full row from list load.

## Goal

1. Soft-load modal fields from warm `groups` when present and !forceRefresh.
2. Coalesce concurrent cold loads for the same groupId.
3. Force path still fetches; save/delete still force-refresh list.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm group present
- [x] Concurrent coalesce
- [x] force path still fetches
- [x] Focused tests green
