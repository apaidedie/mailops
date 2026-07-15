# Soft-load temp-emails and pool-admin on navigate

## Problem

`navigate('temp-emails')` and `navigate('pool-admin')` always call loaders with
`forceRefresh=true`, forcing network + loading overlay even when
`accountsCache['temp']` / `__poolAdminState.cache` already hold warm data.
Overview already soft-loads on dashboard re-entry; these pages should match.

## Goal

1. Navigate re-entry soft-loads (default `forceRefresh=false`).
2. Explicit mutations / refresh buttons keep `forceRefresh=true`.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] navigate uses soft load for temp-emails and pool-admin
- [x] Mutation paths still force-refresh
- [x] Focused tests green
