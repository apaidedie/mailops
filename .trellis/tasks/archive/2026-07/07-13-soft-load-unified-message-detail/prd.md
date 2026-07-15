# Soft-load unified mailbox message detail on re-select

## Problem

`loadUnifiedMailboxMessageDetail` always networks and clears `preview.message`
even when re-selecting the same message that is already warm.

## Goal

1. Soft-load when same mailbox+message detail is warm and !force.
2. Coalesce concurrent loads for the same detail signature.
3. Force path still clears and refetches.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm same message
- [x] Concurrent coalesce
- [x] force path still fetches
- [x] Focused tests green
