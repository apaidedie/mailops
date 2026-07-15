# PRD: Collapse bridge inventory dual rows to legacy_bridge

## Problem

Backend still exposes both `custom_domain_temp_mail` and `legacy_bridge` as separate
provider keys in unified mailbox inventory/facets. They are the same Compatible Temp
Mail Bridge implementation (dual-register for historical sources). Frontend already
collapses operator-facing rows; inventory/facets still double-count or show two chips.

## Goal

- Canonicalize bridge aliases to `legacy_bridge` when building:
  - provider facets
  - mailbox provider inventory
  - provider filter matching
- Do **not** remove dual registration from the provider registry (data/source
  compatibility for stored `source`/`provider_name` values).
- Do **not** change CF/bridge upstream APIs.

## Acceptance

- [x] Facets/inventory merge `custom_domain_temp_mail` (+ runtime aliases) into `legacy_bridge`.
- [x] Filtering by either alias returns the combined set.
- [x] Unit/contract tests green.
- [x] Registry still contains both registered provider classes.

## Non-goals

- Migrating historical DB rows to rewrite source keys.
- Removing `CustomTempMailProvider` / `LegacyBridgeTempMailProvider` dual register.
