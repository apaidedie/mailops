# Unified preview messages/detail/verification paint guards

## Goal
Always warm unified preview soft state for messages/detail/verification, but paint loading/result/error only while isCurrentUnifiedMailboxSurface().

## Done
- [x] loadUnifiedMailboxMessages surface paint guard
- [x] loadUnifiedMailboxMessageDetail surface paint guard
- [x] loadUnifiedMailboxVerification surface paint guard
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
