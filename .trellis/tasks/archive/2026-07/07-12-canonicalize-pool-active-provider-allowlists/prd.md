# Canonicalize pool and active-provider allowlists

## Goal

Collapse bridge aliases when building pool-default datalist, active-mailbox suggestion chips, and pool-admin provider filter options so operators do not see both `custom_domain_temp_mail` and `legacy_bridge`.

## Requirements

- Canonicalize via `normalizeTempMailSettingsProviderName` (or shared alias map) when collecting allowlist/filter values.
- Keep `auto` first for pool defaults.
- Prefer catalog labels on active-mailbox chips when available.
- Contract tests assert canonicalize/dedupe markers.

## Acceptance Criteria

- [x] Pool default + active allowlist builders de-dupe aliases.
- [x] Pool-admin filter normalizes provider keys.
- [x] Focused tests + `git diff --check` pass.
