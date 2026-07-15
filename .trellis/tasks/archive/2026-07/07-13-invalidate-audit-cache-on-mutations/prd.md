# Invalidate audit soft cache on inventory and settings mutations

## Problem

`loadAuditLogPage` soft-loads via `auditLogPageCache`, but nothing calls
`invalidateAuditLogPageCache()`. After account/temp/settings mutations that
write audit rows, re-entering the audit page paints stale data.

## Goal

1. Export invalidate helper on window for cross-module callers.
2. Invalidate on settings save/auto-save success and inventory force-refresh.
3. Invalidate on full/selected/retry token refresh success (ops may be audited).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] window.invalidateAuditLogPageCache exported
- [x] settings save paths invalidate
- [x] account/temp force-refresh invalidates
- [x] refresh success paths invalidate
- [x] Focused tests green
