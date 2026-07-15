# Soft-load tags list when warm cache exists

## Problem

`loadTags()` and `loadTagsForSelect()` always GET `/api/tags`, even when
`allTags` is already warm (re-open tag modal / batch tag after first load).

## Goal

1. `loadTags(forceRefresh=false)` reuses warm `allTags` and re-renders.
2. Create/delete force `loadTags(true)`.
3. `loadTagsForSelect` prefers warm `allTags` (or soft loadTags).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft load when allTags non-empty and !force
- [x] Mutation paths force refresh
- [x] loadTagsForSelect reuses warm allTags
- [x] Focused tests green
