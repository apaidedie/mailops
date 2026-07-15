# Force emails/temp/accounts-by-group supersede soft in-flight

## Problem

`loadEmails(true)`, `loadTempEmails(true)`, and `loadAccountsByGroup(..., true)`
join any in-flight soft GET, so force refresh after soft can paint stale lists.

## Goal

1. Soft joins any in-flight; force joins only force in-flight.
2. Force supersedes soft; abandoned soft must not write list caches.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] emails per-cacheKey loadForce + identity
- [x] tempEmails loadForce + identity
- [x] accountsByGroup per-queryKey loadForce + identity
- [x] Focused tests green
