# Dedupe diagnostics provider lists for bridge aliases

## Goal

Collapse `custom_domain_temp_mail` / `legacy_bridge` (and related aliases) in Settings provider diagnostics summary and console table so operators do not see duplicate Compatible Bridge rows.

## Requirements

- Reuse canonical allowlist helper for temp provider keys.
- De-dupe diagnostics.providers before summary metrics/labels and console render.
- Prefer ready/configured/active flags when merging.
- Contract tests assert markers.

## Acceptance Criteria

- [x] Diagnostics path de-dupes provider rows by canonical key.
- [x] Focused tests + `git diff --check` pass.
