# Coalesce concurrent loadEmails fetches by cacheKey

## Problem

`loadEmails` soft-loads warm `emailListCache[cacheKey]` but cold network loads
for the same email+folder can race (double-click, selectAccount + refresh)
and stampede `/api/emails/...`.

## Goal

1. Share one in-flight promise per `email_folder` cacheKey.
2. Warm soft path unchanged.
3. forceRefresh still networks (shares in-flight for same key when already loading).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] emailsLoadPromises coalesces by cacheKey
- [x] Warm soft path still short-circuits
- [x] Focused tests green
