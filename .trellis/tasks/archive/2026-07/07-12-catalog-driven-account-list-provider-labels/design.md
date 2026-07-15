# Design

## Approach

Rewrite `getProviderLabel(provider)` to look up `mailboxProviderCatalogCache` by provider key. If cache empty and `loadMailboxProviderCatalog` exists, kick a background load (do not block render). Fallback: raw key through `translateAppTextLocal`.

## Call sites

Account card tag generation remains the same; only label resolution changes.

## Compatibility

No DOM id changes. Existing CSS `.account-provider-tag` preserved.
