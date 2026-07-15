# Temp messages/detail current-view paint guard

## Goal
loadTempEmailMessages / getTempEmailDetail always warm soft caches; paint/error/loading only while still on the same temp mailbox.

## Acceptance
- [x] messages: warm always; paint only currentAccount === targetEmail
- [x] detail: isCurrentTempMailbox guard; warm always
- [x] contracts green
