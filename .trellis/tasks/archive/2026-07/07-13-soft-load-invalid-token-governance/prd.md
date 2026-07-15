# Soft-load invalid-token governance candidates

## Problem

`loadInvalidTokenGovernanceCandidates` always GETs
`/api/accounts/invalid-token-candidates`, and `resetInvalidTokenGovernanceState`
clears the in-memory list on every refresh-modal open, forcing a network hit.

## Goal

1. Soft-load warm candidates on modal re-open.
2. Coalesce concurrent soft loads.
3. Force-refresh after refresh complete / batch inactive / batch delete.
4. reset/hide only clear UI, not soft cache (unless invalidate).
5. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path reuses warm loaded candidates without network
- [x] showRefreshModal uses soft load
- [x] Mutation paths force-refresh
- [x] Focused tests green
