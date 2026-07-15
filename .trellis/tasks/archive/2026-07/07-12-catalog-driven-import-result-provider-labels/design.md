# Design

## Approach

Add `getImportResultProviderLabel(providerKey)` that:

1. Normalizes key
2. Looks up `mailboxProviderCatalogCache` (if present) by provider key (any kind)
3. Falls back to `providerOptions` (import selector cache)
4. Falls back to known alias labels only if present in catalog notes/labels is unavailable → raw key

No second provider registry. Alias display for legacy temp keys should come from catalog entries/aliases when present; otherwise raw key is acceptable.

## Call site

Replace hard-coded map in auto-import success toast with the helper.

## Compatibility

Toast text remains multi-line plain text. No DOM structure change.
