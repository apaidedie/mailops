# Clear email soft caches after account import success

## Goal
addAccount success clears emailListCache for parsed import addresses (overwrite-safe).

## Acceptance
- [ ] extractImportCandidateEmails
- [ ] clearEmailListCacheForMailboxes on success
- [ ] contract green
