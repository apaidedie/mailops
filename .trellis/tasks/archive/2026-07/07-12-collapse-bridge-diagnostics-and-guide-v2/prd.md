# Collapse dual bridge rows in diagnostics and integration guide

## Problem

Registry keeps both `custom_domain_temp_mail` and `legacy_bridge` for stored-source
compatibility. Inventory/facets already collapse; frontend guide cards dedupe; but
backend `provider_diagnostics` and `provider_integration_guide` still emitted two
identical-label rows for external API consumers.

## Goal

1. Collapse Compatible Temp Mail Bridge dual-register keys to `legacy_bridge` in
   diagnostics and integration-guide provider lists.
2. Keep registry dual-register + full catalog lookup for runtime/source compatibility.
3. Recompute diagnostics summary from collapsed rows.
4. Preserve pool-claim alias maps that intentionally list both source names.

## Acceptance Criteria

- [x] Diagnostics providers list has at most one of `custom_domain_temp_mail` / `legacy_bridge`
- [x] Integration guide providers list has at most one of those keys
- [x] Collapsed row is `legacy_bridge`
- [x] Diagnostics summary totals match collapsed provider list length
- [x] Focused unit tests + `git diff --check` pass
