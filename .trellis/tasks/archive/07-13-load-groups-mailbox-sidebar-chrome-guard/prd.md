# loadGroups mailbox sidebar chrome guard

## Goal
Prevent loadGroups cold-path loading/error chrome from flashing #groupList when called off the mailbox page (pool-admin/export/batch-move). Guard rerenderAccountCaches to standard mailbox only.

## Done
- [x] isCurrentMailboxGroupsSurface() + paintSidebarChrome in loadGroups
- [x] rerenderAccountCaches mailbox + !isTempEmailGroup guard
- [x] contract test + quality-guidelines
- [x] node --check + unittest + git diff --check
