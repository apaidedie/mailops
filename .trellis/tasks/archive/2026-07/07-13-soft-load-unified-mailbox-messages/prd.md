# Soft-load unified mailbox messages on re-open

## Problem

`loadUnifiedMailboxMessages` always networks even when re-opening the same
mailbox preview without force and messages are already warm in preview state.

## Goal

1. Soft-load when same mailbox key/folder and warm messages and !force.
2. Coalesce concurrent loads for the same key/folder.
3. openUnifiedMessagePreview / force still networks.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm same key/folder
- [x] Concurrent coalesce
- [x] force path still fetches
- [x] Focused tests green
