# Soft-load unified mailbox directory on re-entry

## Problem

`switchMailboxViewMode('unified')` and mailbox navigate call
`loadUnifiedMailboxes(false)`, but the loader still always GETs `/api/mailboxes`
even when the same filter/page signature was just loaded. Other pages already
soft-load warm caches on re-entry.

## Goal

1. Cache last successful directory payload + request signature.
2. Soft re-entry with matching signature re-renders from cache (no network).
3. Force refresh / filter/search/page changes still network.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft load reuses warm payload when signature matches
- [x] forceRefresh always networks
- [x] Mutations/filters still call loadUnifiedMailboxes(true)
- [x] Focused tests green
