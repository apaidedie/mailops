# Soft-load token-tool config and account options

## Problem

`loadOAuthConfig` and `loadAccountOptions` always network. Re-opening save dialog
or re-entering token-tool re-fetches the same payloads without soft cache or
in-flight coalesce.

## Goal

1. Soft-load warm config/accounts caches with forceRefresh support.
2. Coalesce concurrent soft/force network loads.
3. Force after successful save (accounts may change).
4. Contract tests + node --check + git diff --check pass.

## Acceptance Criteria

- [x] loadOAuthConfig soft-loads warm config
- [x] loadAccountOptions soft-loads warm accounts
- [x] openSaveDialog soft; post-save force accounts
- [x] Focused tests green
