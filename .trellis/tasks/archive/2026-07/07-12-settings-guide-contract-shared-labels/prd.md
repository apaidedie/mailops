# Settings guide and contract labels use shared helper

## Goal

Route Settings provider-integration guide cards, provider-contract status rows, and schema-panel provider titles through `resolveMailboxProviderLabel`.

## Confirmed Facts

- Shared helper already owns labels for account/import/pool/temp/unified surfaces.
- Guide/contract/schema panel still use payload `label` directly at render time.
- These panels already run after catalog load, so soft-load is usually unnecessary.

## Requirements

- Prefer shared catalog labels for guide cards, contract rows, and schema panel titles.
- Keep payload label/display_name as fallback.
- Contract tests assert shared-helper usage at those call sites.

## Acceptance Criteria

- [x] Integration guide card labels use shared resolution.
- [x] Provider contract status row labels use shared resolution.
- [x] Schema panel provider title uses shared resolution.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing guide/contract backend payloads.
- Unifying plugin config panel save path.
