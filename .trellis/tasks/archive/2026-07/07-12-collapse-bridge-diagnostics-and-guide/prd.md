# Collapse dual bridge rows in diagnostics and integration guide

## Problem

Registry keeps both `custom_domain_temp_mail` and `legacy_bridge` for stored-source
compatibility. Inventory/facets already collapse to `legacy_bridge`, and the frontend
dedupes guide cards — but **backend** `provider_diagnostics` and
`provider_integration_guide` still emit two identical-label rows.

Evidence (local, empty DB):

- diagnostics `summary.temp=7` with both bridge providers `ready`
- guide `providers` contains both under label `Compatible Temp Mail Bridge`
- External API consumers (no frontend dedupe) see a false dual-provider surface

## Goal

1. Collapse Compatible Temp Mail Bridge dual-register keys to `legacy_bridge` in
   diagnostics and integration-guide provider lists.
2. Keep registry dual-register + full catalog lookup for runtime/source compatibility.
3. Recompute diagnostics summary from collapsed rows.
4. Preserve pool-claim alias maps that intentionally list both source names.

## Non-goals

- Removing `CustomTempMailProvider` / `LegacyBridgeTempMailProvider` registration
- Changing default settings value migration (`custom_domain_temp_mail` default)
- Changing CF/bridge upstream APIs

## Acceptance Criteria

- [x] Diagnostics providers list has at most one of `custom_domain_temp_mail` / `legacy_bridge`
- [x] Integration guide providers list has at most one of those keys
- [x] Collapsed row is `legacy_bridge` and retains bridge aliases including `custom_domain_temp_mail`
- [x] Diagnostics summary totals match collapsed provider list length
- [x] Focused unit tests + `git diff --check` pass
