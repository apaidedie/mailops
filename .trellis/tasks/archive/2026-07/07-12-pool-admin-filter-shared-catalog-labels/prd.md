# Pool admin filter uses shared catalog labels

## Goal

Keep pool-admin provider filter options/labels synchronized with the shared catalog helper and refresh them when the boot/settings catalog load completes.

## Confirmed Facts

- Pool admin already builds options from `mailbox_providers` / catalog cache.
- Shared `resolveMailboxProviderLabel` now owns label lookup for account cards and import results.
- Catalog preload on boot may finish after pool admin first open in some navigation orders; force-refresh on catalog success avoids stale options.

## Requirements

- Prefer shared label helper when resolving option labels.
- On catalog load success, refresh pool-admin provider options if the helper exists.
- Keep empty “所有类型” option and current selection preservation.
- Contract tests cover shared-label usage and catalog-success refresh call.

## Acceptance Criteria

- [x] Pool admin option labels use shared catalog label resolution when available.
- [x] Catalog load success path can refresh pool-admin provider options.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing pool-admin query backend semantics.
- Redesigning pool-admin toolbar UI.
