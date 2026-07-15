# Clear email soft caches when accounts are deleted

## Problem
Account delete cleared inventory/detail account caches but left emailListCache/emailDetailCache for that mailbox; soft re-select could paint orphan mail.

## Goal
clearEmailListCacheForMailbox(es) + call sites on single/batch/governance deletes.

## Acceptance
- [ ] helper + window exports
- [ ] deleteCurrentAccount / deleteAccount / batchDelete / invalid-token batch
- [ ] contract tests green
