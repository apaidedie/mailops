# Canonicalize active mailbox textarea matching

## Goal

Keep active-mailbox suggestion chips and textarea values consistent after alias canonicalization: read/write/compare using canonical provider keys, and resolve catalog labels via aliases.

## Problem / evidence

- Chips now use canonical keys (`legacy_bridge`), but textarea may still hold `custom_domain_temp_mail`.
- `selected.has(value)` fails to mark chips active; toggle may append duplicates instead of removing aliases.

## Requirements

- Canonicalize values when reading textarea lines.
- Canonicalize on toggle add/remove.
- Prefer writing canonical keys back to textarea when chips are used.
- `getMailboxProviderCatalogLabel` should look up by canonical key as well as raw key.
- Contract tests assert markers.

## Acceptance Criteria

- [x] Textarea read/toggle paths canonicalize provider keys.
- [x] Catalog label lookup tries canonical alias keys.
- [x] Focused tests + `git diff --check` pass.
