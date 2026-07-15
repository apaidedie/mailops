# Bridge allowlist treats dual-register keys as one family

## Problem

Compatible Temp Mail Bridge dual-registers `custom_domain_temp_mail` and
`legacy_bridge`. Runtime aliases (`gptmail`, …) already treat either catalog
key as active when the family intersects the allowlist, but the two catalog
keys themselves do **not**:

Evidence (patched allowlist):

- allowlist `{legacy_bridge}` → `custom_domain_temp_mail` inactive, `gptmail` active
- allowlist `{custom_domain_temp_mail}` → `legacy_bridge` inactive, `gptmail` active

Operators enabling only one bridge key leave the twin catalog key inactive even
though they are the same implementation. Stored inventory may use either source.

## Goal

1. Treat GPTMAIL pool temp provider names as one active family in allowlist checks.
2. Keep empty allowlist meaning “all active”.
3. Do not change CF/bridge upstream APIs or remove dual registry.

## Acceptance Criteria

- [x] `is_mailbox_provider_active("temp", "custom_domain_temp_mail")` is true when allowlist has only `legacy_bridge`
- [x] Symmetric for allowlist-only `custom_domain_temp_mail`
- [x] Non-bridge providers unchanged
- [x] Focused tests + `git diff --check` pass
