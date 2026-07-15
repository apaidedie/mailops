# Seed emailListCache from compact account pull

## Problem

`refreshCompactAccount` fetches inbox/junkemail lists but only updates account
summary. Switching back to standard view soft-loads empty/stale `emailListCache`.

## Goal

1. On successful compact pull, upsert `emailListCache` per folder via shared helper.
2. Clear warm email detail cache for those folders so detail soft-load stays safe.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Uses cacheBatchFetchedFolder (or equivalent upsert)
- [x] Folder mapping preserved for inbox + junkemail
- [x] Detail cache cleared for pulled folders
- [x] Focused tests green
