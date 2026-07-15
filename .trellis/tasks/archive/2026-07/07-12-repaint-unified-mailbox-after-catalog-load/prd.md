# Repaint unified mailbox after catalog load

## Goal

When the shared mailbox provider catalog finishes loading, repaint already-visible unified mailbox cards and readiness/capability labels so they no longer stick on first-paint raw keys.

## Confirmed Facts

- Account tags already repaint via `refreshAccountProviderTagsFromCatalog`.
- Unified cards/readiness use shared label helpers but only re-render on data reload.
- `unifiedMailboxState.items` caches the last directory page.

## Requirements

- On catalog success, repaint unified list from cached items when loaded.
- Also re-render provider context / capability matrix when last provider_context is available.
- Do not force a full `/api/mailboxes` network reload.
- Contract tests assert the refresh helper and catalog-success call site.

## Acceptance Criteria

- [x] Catalog success triggers a non-network unified mailbox label repaint when data is already loaded.
- [x] Focused tests + `git diff --check` pass.

## Out Of Scope

- Changing `/api/mailboxes` payloads.
- Auto-switching into unified mode.
