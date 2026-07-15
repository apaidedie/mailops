# Soft-load settings page on navigate re-entry

## Problem

`navigate('settings')` always GETs `/api/settings` even when the operator just
left and returned with no saves. Other pages already soft-load warm caches.

## Goal

1. Cache successful GET `/api/settings` payload for soft re-entry.
2. Invalidate cache after any successful settings save (manual or auto).
3. `forceRefresh=true` still forces network.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadSettings soft-loads warm cache by default
- [x] navigate/showSettingsModal use soft load
- [x] saveSettings + autoSaveSettings invalidate cache
- [x] Focused tests green
