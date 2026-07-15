# Soft-load showEditAccountModal detail cache

## Problem

`showEditAccountModal` always GETs `/api/accounts/<id>` even when re-opening the
same account after a successful detail fetch in the same session.

## Goal

1. Soft-load warm account detail when !forceRefresh.
2. Coalesce concurrent loads for the same accountId.
3. Invalidate cache on successful update/delete.
4. Do NOT paint from list cache (list truncates client_id).
5. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm detail present
- [x] Concurrent coalesce
- [x] Update/delete invalidates cache
- [x] Focused tests green
