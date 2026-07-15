# Design

## Approach

Reuse existing `loadMailboxProviderCatalog()` payload. Cache `selection_policy` from `/api/providers` and render `#poolDefaultProviderOptions` options from `scopes.pool_claim_default.allowed_values`.

## Data flow

`/api/providers` → cache selection_policy → `renderPoolDefaultProviderDatalist()` → `#poolDefaultProviderOptions` option nodes.

## Compatibility

- Input remains free text; datalist is suggestion-only.
- Backend still validates on save.
- Empty catalog falls back to `auto` only (or keeps existing options if mount missing).

## Trade-offs

MVP only updates the Settings pool-default datalist, not pool-admin filters, to keep scope small and high value.
