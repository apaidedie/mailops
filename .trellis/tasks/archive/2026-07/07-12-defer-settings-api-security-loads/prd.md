# Defer Settings contract-check and readiness loads until API security tab

## Problem

Every Settings open (`loadSettings`) soft-loads:
- `/api/settings/external-api/contract-check`
- operational readiness snapshot (`/api/mailboxes?...`)

even when the user stays on Basic / Temp Mail / other tabs. `switchSettingsTab('api-security')`
already loads these when the API security tab becomes active.

## Goal

1. Remove eager contract-check / operational-readiness loads from every `loadSettings`.
2. Keep soft-load when Settings opens already on `api-security` tab.
3. Keep soft-load when switching to `api-security`.
4. Keep force-load after API security save mutations.

## Acceptance Criteria

- [x] `loadSettings` does not always call both loaders
- [x] Opening/switching to `api-security` still soft-loads both
- [x] Save paths still force-refresh when required
- [x] Focused tests + `node --check` + `git diff --check` pass
