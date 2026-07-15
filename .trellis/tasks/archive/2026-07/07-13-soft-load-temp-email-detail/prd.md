# Soft-load temp email message detail on re-select

## Problem

`getTempEmailDetail` always networks and shows a loading spinner even when
re-selecting the same temp message that was already loaded.

## Goal

1. Soft-load when same mailbox+message detail is warm and !forceRefresh.
2. Coalesce concurrent loads for the same detail key.
3. Invalidate cache on mailbox delete / message list force refresh paths as needed.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm same message
- [x] Concurrent coalesce
- [x] Force/list refresh invalidation remains safe
- [x] Focused tests green
