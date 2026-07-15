# Coalesce concurrent loadTempEmails fetches

## Problem

`loadTempEmails` soft-loads warm `accountsCache['temp']` but cold network loads
can race (navigate + generate callback, double open) and stampede `/api/temp-emails`.

## Goal

1. Share one in-flight promise for concurrent soft/force network loads.
2. Warm soft path unchanged.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] tempEmailsLoadPromise coalesces concurrent network loads
- [x] Warm soft path still short-circuits
- [x] Focused tests green
