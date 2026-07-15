# Canonicalize operator-facing default temp provider to legacy_bridge

## Problem

After collapsing Compatible Temp Mail Bridge dual-register rows in diagnostics
and `provider_integration_guide`, operator/API defaults still advertise
`temp_mail_provider=custom_domain_temp_mail`, which is **no longer present** in
the guide provider list. External integrators see a default that does not match
the operator-facing provider catalog.

Evidence (local empty DB):

- `defaults.temp_mail_provider == custom_domain_temp_mail`
- guide temp providers include `legacy_bridge` only (not `custom_domain_temp_mail`)

## Goal

1. Project operator-facing default temp provider through the same bridge
   canonicalization as diagnostics/guide (`legacy_bridge`).
2. Do **not** migrate stored settings or change registry dual-register.
3. Keep runtime resolution accepting `custom_domain_temp_mail` as a valid name.

## Non-goals

- Changing `DEFAULT_TEMP_MAIL_PROVIDER` storage default migration
- Removing dual registry classes
- Changing CF/bridge upstream APIs

## Acceptance Criteria

- [x] Capabilities/providers discovery `defaults.temp_mail_provider` is operator-canonical when stored/default is a bridge alias
- [x] Guide still contains the projected default provider key
- [x] Stored settings may still be `custom_domain_temp_mail`; runtime still works
- [x] Focused tests + `git diff --check` pass
