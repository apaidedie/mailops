# Refresh-stats + unified directory paint guards

## Goal
Paint refresh-stats only while refresh modal is open (null-safe DOM). Paint unified directory loading/result only on unified mailbox surface with matching query signature.

## Done
- [x] applyRefreshStats null-safe + loadRefreshStats modal paint guard
- [x] isCurrentUnifiedMailboxSurface / isCurrentUnifiedDirectoryView in loadUnifiedMailboxes
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
