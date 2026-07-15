# Refresh import providers after catalog load

## Goal

When the shared mailbox provider catalog finishes loading, refresh the import-account provider selector if present so labels/options stay aligned without waiting for the next modal open.

## Confirmed Facts

- Catalog success already refreshes account tags and pool-admin options.
- Import selector is filled by `loadProviders()` mainly when opening the add-account modal.
- If catalog arrives after a modal open that used offline fallback, options can stay stale until reopened.

## Requirements

- On catalog success, call import `loadProviders(true)` when the helper exists.
- Keep offline/auto-outlook fallback behavior unchanged.
- Contract tests assert the catalog-success refresh call.

## Acceptance Criteria

- [x] Catalog success path refreshes import provider options via shared helper.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing import backend APIs.
- Auto-opening the import modal.
