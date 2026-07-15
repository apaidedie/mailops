# Stop forcing preflight refresh after temp-mail and closed Settings saves

## Problem

After temp-mail auto-save and global Settings save, the UI still force-loads
`/api/providers/preflight` (and global save also force-loads operational readiness)
even though:

1. Preflight UI lives under API security / workbench
2. Global save closes the Settings modal immediately after success

Catalog force-refresh after temp-mail save remains correct.

## Goal

1. Temp-mail save: force catalog only; invalidate preflight cache without network.
2. Global Settings save: force catalog; invalidate preflight/readiness/contract caches
   without network (modal is closing).
3. API security auto-save still force-refreshes preflight/contract/readiness.

## Acceptance Criteria

- [x] temp-mail save path does not call `loadProviderPreflightSnapshot(true, false)`
- [x] global save path does not force preflight/readiness network after close
- [x] api-security save still force-refreshes preflight
- [x] Focused tests + node --check + git diff --check pass
