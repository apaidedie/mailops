# loadMoreEmails current-view paint guard

## Goal
Prevent loadMoreEmails from merging/painting a page into the wrong live email list when the user switches mailbox/folder mid-request.

## Done
- [x] Capture targetEmail/folder/method/skip + baseline at request start
- [x] Always upsert emailListCache for target key from baseline merge
- [x] Paint loading/list/error only while isCurrentEmailListView()
- [x] Contract test + quality-guidelines
- [x] node --check + unittest + git diff --check
