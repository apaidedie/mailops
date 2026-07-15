# Clear email soft caches when account email/credentials update

## Goal
updateAccount clears emailListCache for previous/next address when email or mail credentials change.

## Acceptance
- [ ] editEmail.dataset.originalValue
- [ ] shouldClearMailSoftCache path
- [ ] contract tests green
