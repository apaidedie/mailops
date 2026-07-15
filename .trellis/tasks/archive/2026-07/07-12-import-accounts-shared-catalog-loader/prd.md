# Import accounts use shared catalog loader

## Goal

Route the import-account provider selector through the shared `loadMailboxProviderCatalog` cache/loader instead of always issuing a parallel `/api/providers` fetch.

## Confirmed Facts

- Import already builds options from `mailbox_providers` (account kind) with legacy `providers` fallback.
- Shared catalog cache is the same `mailbox_providers` array returned by `/api/providers`.
- Boot preload and plugin lifecycle keep the shared cache warm.

## Requirements

- Prefer warm shared cache, then shared loader, then direct fetch fallback.
- Keep offline auto/outlook fallback when catalog is unavailable.
- Preserve auto-first ordering and provider notes.
- Contract tests assert shared-loader preference.

## Acceptance Criteria

- [x] Import `loadProviders` uses shared catalog cache/loader before direct fetch.
- [x] Offline fallback remains for empty/unavailable catalog.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing import backend APIs or account validation.
- Wiring catalog-success repaint of the import modal (optional follow-up).
