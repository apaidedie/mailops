# Force ensurePoolAdminProviderOptions reload shared catalog

## Problem
ensurePoolAdminProviderOptions(true) still soft-applied warm catalog and only forced load when cache was empty array.

## Goal
Soft paints warm catalog; force always loadMailboxProviderCatalog(true) (or empty warm).

## Acceptance
- [ ] !force && applyFromCache early return
- [ ] forceCatalogLoad = force || emptyWarmCache
- [ ] contract tests green
