# selectEmail current-view paint guard

## Goal
Capture mailbox/folder/method at request start; always warm emailDetailCache; paint/error/loading only while isCurrentMailboxFolderMethod().

## Acceptance
- [x] isCurrentMailboxFolderMethod guard
- [x] warm cache always; paint only when current
- [x] contracts green
