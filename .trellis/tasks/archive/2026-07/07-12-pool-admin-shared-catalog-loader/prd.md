# Pool admin uses shared catalog loader

## Goal

Stop pool-admin from issuing a parallel `/api/providers` fetch when the shared `loadMailboxProviderCatalog` path already owns catalog cache lifecycle.

## Confirmed Facts

- Pool admin prefers `mailboxProviderCatalogCache` when populated.
- Catalog success already calls `ensurePoolAdminProviderOptions(true)`.
- Boot preload and plugin lifecycle also refresh the shared catalog.
- Direct `fetch('/api/providers')` remains only as last-resort fallback when the shared loader is unavailable.

## Requirements

- Prefer shared cache, then shared loader, then direct fetch fallback.
- `forceRefresh` continues to mean re-apply even if options already loaded (not an infinite re-fetch loop).
- Contract tests assert shared-loader preference and retain fallback markers only as secondary path.

## Acceptance Criteria

- [x] Pool admin uses `loadMailboxProviderCatalog` before direct `/api/providers` fetch.
- [x] Catalog success re-apply path still works without recursive re-fetch.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing pool-admin query/filter backend semantics.
- Removing all dual DOM plugin injection.
