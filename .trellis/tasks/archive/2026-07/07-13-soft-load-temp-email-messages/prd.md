# Soft-load and coalesce temp email messages

## Problem

`loadTempEmailMessages` always GETs `/api/temp-emails/{email}/messages` even when
re-selecting the same temp mailbox, and concurrent selects can race network.

## Goal

1. Soft-load warm message list by email when !forceRefresh.
2. Coalesce concurrent loads for the same email.
3. Explicit refresh forces network.
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] Soft cache by email
- [x] In-flight coalesce by email
- [x] Refresh forces reload
- [x] Focused tests green
