# Soft-load system version-check session cache

## Problem

`checkVersionUpdate` always GETs `/api/system/version-check` with no session
reuse or in-flight coalesce if invoked more than once.

## Goal

1. Soft-load warm session result when !forceRefresh.
2. Coalesce concurrent checks.
3. forceRefresh still networks; boot delay path remains soft default.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path reuses warm payload
- [x] Concurrent coalesce
- [x] force path still fetches
- [x] Focused tests green
