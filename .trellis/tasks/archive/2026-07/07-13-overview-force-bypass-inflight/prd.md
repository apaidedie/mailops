# Force overview tab reload bypasses in-flight soft load

## Problem

After loadPromises coalesce, `forceReload=true` still joined any in-flight soft
GET, so Refresh / overview-data-changed could paint a soft response instead of
starting a true network refresh.

## Goal

1. Soft loads coalesce with soft in-flight only.
2. Force supersedes soft in-flight and starts a new GET.
3. Concurrent force loads still coalesce with each other.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft joins soft only
- [x] Force supersedes soft
- [x] Force joins force
- [x] Focused tests green
