# Soft-load unified mailbox verification on re-run

## Problem

`loadUnifiedMailboxVerification` always networks even when re-running extraction
for the same mailbox/folder with warm verification already painted, and concurrent
double-clicks fire multiple GETs.

## Goal

1. Soft-load when same key|folder verification is warm and !force.
2. Coalesce concurrent loads for the same verification signature.
3. Explicit force path still refetches; list refresh clears signature.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft path skips network when warm same signature
- [x] Concurrent coalesce
- [x] force path still fetches
- [x] Focused tests green
