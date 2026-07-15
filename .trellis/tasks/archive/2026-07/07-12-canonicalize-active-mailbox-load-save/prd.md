# Canonicalize active mailbox load and save paths

## Goal

When loading settings into the active-mailbox textarea and when collecting the save payload, canonicalize bridge aliases so stored/submitted values match chip suggestion keys.

## Requirements

- loadSettings uses `setActiveMailboxProvidersTextarea` (canonical write).
- API security collect path uses `getActiveMailboxProvidersFromTextarea` (canonical read).
- Optionally canonicalize `pool_default_provider` on load/save.
- Contract tests assert markers.

## Acceptance Criteria

- [x] Load path writes canonical active providers.
- [x] Save path collects canonical active providers.
- [x] Focused tests + `git diff --check` pass.
