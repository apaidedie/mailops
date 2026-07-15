# Coalesce loadPoolAdmin and key soft cache by query

## Problem

`loadPoolAdmin` soft-loads the last response without checking current filters, and
concurrent cold loads can stampede `/api/pool-admin/accounts` while `loading` is true.

## Goal

1. Soft-load only when warm cache query signature matches current filters/page.
2. Coalesce concurrent network loads for the same query signature.
3. forceRefresh still networks.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft cache keyed by query signature
- [x] In-flight promise coalesce by query signature
- [x] Focused tests green
