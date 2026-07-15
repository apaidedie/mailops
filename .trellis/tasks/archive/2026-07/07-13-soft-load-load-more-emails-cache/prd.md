# Persist emailListCache on loadMoreEmails

## Problem

`loadMoreEmails` only mutates `emailListCache[cacheKey]` when the key already
exists. After cold first-page load races or missing cache seed, paginated pages
are lost on soft re-select via `loadEmails(false)`.

## Goal

1. Always upsert `emailListCache` after successful load-more (create if missing).
2. Include method + emails + has_more + skip fields matching loadEmails shape.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Upsert path (not only if exists)
- [x] Fields match loadEmails cache shape
- [x] Focused tests green
