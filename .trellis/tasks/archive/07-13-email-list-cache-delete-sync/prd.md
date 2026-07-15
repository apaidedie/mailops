# Sync emailListCache after message delete

## Problem
deleteEmails filtered currentEmails but left emailListCache stale; soft re-select repainted deleted rows.

## Goal
Upsert emailListCache (and temp messages soft cache) after successful deletes.

## Acceptance
- [ ] deleteEmails upserts emailListCache
- [ ] deleteCurrentTempEmailMessage upserts tempEmailMessagesCache
- [ ] contract tests green
