# applyLoadedGroups mailbox surface paint guard

## Goal
Off-page soft/force loadGroups must warm global groups without rewriting mailbox sidebar or refreshing account inventory.

## Done
- [x] isCurrentMailboxGroupsSurface moved above applyLoadedGroups
- [x] renderGroupList / compact strip gated to mailbox surface
- [x] account inventory refresh only on mailbox surface
- [x] language soft-paint group list gated
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
