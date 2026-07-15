# loadEmails current-view paint guard

## Goal
Capture targetEmail/folder/method at request start; warm cache always; paint/error/loading only while isCurrentEmailListView().

## Acceptance
- [x] isCurrentEmailListView guard
- [x] fixed fetch URL uses targetEmail/targetFolder/requestMethod
- [x] contracts green
