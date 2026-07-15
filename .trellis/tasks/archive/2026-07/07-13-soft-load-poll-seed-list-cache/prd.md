# Seed emailListCache from poll engine fetches

## Problem

`pollSingleEmail` / `startPoll` baseline fetch inbox+sentitems but only use
message ids for baseline and account_summary. Opening the mailbox still
soft-loads empty/stale `emailListCache`.

## Goal

1. Helper seeds list cache per folder from successful poll payloads.
2. Used by startPoll baseline + pollSingleEmail success path.
3. Prefer `cacheBatchFetchedFolder`; fallback upsert `emailListCache`.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Helper + folder mapping inbox/sentitems
- [x] startPoll baseline seeds cache
- [x] pollSingleEmail seeds cache
- [x] Focused tests green
