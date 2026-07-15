# Invalidate unified mailbox directory cache on mutations

## Problem

Unified directory soft-load can paint stale rows after account/temp inventory
mutations that never call `loadUnifiedMailboxes(true)`.

## Goal

1. Force-refresh of account lists or temp emails invalidates unified directory soft cache.
2. Soft re-entry after mutation refetches network.
3. Contract tests + node --check pass.

## Acceptance Criteria

- [x] loadAccountsByGroup(force) invalidates unified directory cache
- [x] loadTempEmails(force) invalidates unified directory cache
- [x] invalidate helper is window-reachable for other callers
- [x] Focused tests green
