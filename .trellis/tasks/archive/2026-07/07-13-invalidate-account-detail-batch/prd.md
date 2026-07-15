# Invalidate account detail cache on batch mutations

## Problem

`showEditAccountModal` soft-loads warm detail, but batch delete/status paths
in main.js do not invalidate `accountDetailCache`, so re-open can paint stale
status/group after bulk ops.

## Goal

1. Expose `window.invalidateAccountDetailCache` for cross-feature callers.
2. Batch delete / batch status / invalid-token bulk paths invalidate affected ids.
3. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] window helper exported
- [x] batchDeleteAccounts invalidates
- [x] batch invalid-token delete/status invalidates
- [x] Focused tests green
