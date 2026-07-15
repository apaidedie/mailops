# Soft ensurePoolAdminProviderOptions re-paints warm catalog before early-return

## Goal
Soft path always applyFromCache first; only skip network when painted and catalog still cold.

## Acceptance
- [ ] soft paint before skip
- [ ] contract green
