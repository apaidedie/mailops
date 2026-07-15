# Defer provider preflight load until API security tab

## Problem

`loadSettings` still soft/force-loads `/api/providers/preflight` on every Settings open
via `loadProviderPreflightSnapshot(forceCatalogLoad, false)`, even when the active tab
is Basic/Temp Mail. The preflight console lives under API security / provider workbench.

Contract-check and operational readiness were already gated to `api-security`; preflight
should match.

## Goal

1. Do not load provider preflight on every Settings open.
2. Soft-load preflight when opening/switching to `api-security` (or loadSettings while already on that tab).
3. Keep force-refresh after api-security / temp-mail save mutations that already force preflight.

## Acceptance Criteria

- [x] `loadSettings` does not always call `loadProviderPreflightSnapshot`
- [x] `api-security` tab path soft-loads preflight
- [x] Save force paths preserved
- [x] Focused tests + `node --check` + `git diff --check` pass