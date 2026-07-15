# Soft-load export group list via loadGroups

## Problem

`loadExportGroupList` only paints when `groups.length > 0`. Opening export with
cold groups shows empty instead of soft-loading via shared `loadGroups`.

## Goal

1. When groups cold, soft-load via `loadGroups(false)`.
2. Then render from warm groups.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadExportGroupList awaits loadGroups(false) when cold
- [x] Renders from groups after soft load
- [x] Focused tests green
