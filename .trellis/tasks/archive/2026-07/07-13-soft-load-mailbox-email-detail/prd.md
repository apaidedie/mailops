# Soft-load mailbox selectEmail detail on re-select

## Problem

`selectEmail` always networks and shows a loading spinner even when
re-selecting the same Outlook/IMAP message that was already loaded.

## Goal

1. Soft-load when same account|folder|method|messageId detail is warm and !forceRefresh.
2. Coalesce concurrent loads for the same detail key.
3. Invalidate on list force-refresh / delete as needed.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm same message
- [x] Concurrent coalesce
- [x] Force/list refresh invalidation remains safe
- [x] Focused tests green
