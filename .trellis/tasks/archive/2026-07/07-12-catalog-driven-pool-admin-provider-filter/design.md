# Design

## Approach

Mirror `ensurePoolAdminGroupOptions`: add `ensurePoolAdminProviderOptions()` that fills `#poolAdminProviderFilter` from mailbox provider catalog.

## Data source priority

1. `mailboxProviderCatalogCache` when already loaded by main.js
2. Else `fetch('/api/providers')` → `mailbox_providers`

## Option rules

- Always first option: empty value + translated “所有类型”
- One option per unique `provider` key from catalog items
- Skip empty / `auto`
- Label: `item.label || item.provider_label || provider`
- Preserve selected value if still present after rebuild

## Integration points

- Call from `loadPoolAdmin()` before query (same as groups)
- Optionally refresh after `loadMailboxProviderCatalog` success when on pool-admin page (nice-to-have; load-on-open is enough for MVP)

## Compatibility

- Empty selection still means no provider filter
- Backend accepts any provider string; invalid values simply yield empty results
